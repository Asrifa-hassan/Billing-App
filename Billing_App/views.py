from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q,F
from .models import Product, UserProfile
from django.template.loader import get_template
from django.http import HttpResponse
from datetime import datetime
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import json
from xhtml2pdf import pisa
from django.db.models import Sum,Q
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from .models import Customer, Product, Cart, CartItem, InvoiceItem
from decimal import Decimal
from django.views.decorators.http import require_POST
from .models import Invoice
from django.views.decorators.cache import never_cache
from django.db.models import CharField
from django.views.decorators.csrf import csrf_exempt
from .models import *


# Create your views here.
def index(request):
  return render(request,'index.html')

def login_page(request):
  if request.user.is_authenticated:
    return redirect('dashboard')

  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")
    user = authenticate(username=email, password=password)
    if user is not None:
      if user.is_staff == 1:
        # admin/staff module
        login(request, user)
        return redirect('dashboard')
      else:
        messages.warning(request, "You are not authorized as staff yet. Please wait for admin approval.")
    else:
      if not User.objects.filter(username=email).exists():
        messages.warning(request, "You are not registered yet. Please register..!")
        return redirect('register')
      else:
        messages.error(request, "Wrong password")
        return redirect('login_page')
  return render(request, 'login.html')

def logout_page(request):
  logout(request)
  return redirect('index')

def register(request):
  if request.method == "POST":
    email = request.POST.get("email")
    f_name = request.POST.get("f_name")
    l_name = request.POST.get("l_name")
    password = request.POST.get("password")
    try:
      User.objects.get(username=email)
      messages.warning(request, "Email already exist. Please login...!!")
      return redirect('login_page')
    except User.DoesNotExist:
      user = User.objects.create(
        username=email,
        email=email,
        first_name=f_name,
        last_name=l_name,
        password=password,
      )
      user.set_password(password)
      user.save()
      messages.success(request, "Account created succesfully. Please login with your credentials")
    return redirect('login_page')
  return render(request, 'register.html')

def forgot_password(request):
  if request.method == 'POST':
    email = request.POST.get('email')
    password = request.POST.get('password')
    try:
      user = User.objects.get(username=email)
      user.set_password(password)
      user.save()
      messages.success(request, "Password changed successfully.")
      return redirect('login_page')
    except User.DoesNotExist:
      messages.error(request, "Email not found. Please register first.")
      return redirect('register')
  return render(request, 'forgot_password.html')

@never_cache
@login_required
def dashboard(request):
    invoices=Invoice.objects.all().count()
    customers=Customer.objects.all().count()
    products_count=Product.objects.all().count()
    products_lt10=Product.objects.filter(stock__lt=5)
    staffs=User.objects.filter(is_staff=True,is_superuser=False).count()

    today = timezone.now().date()
    recent_invoice=Invoice.objects.filter(date__date=today).order_by('-id')
    total_invoice_amount=Invoice.objects.all().aggregate(total_sum=(Sum('grand_total')))['total_sum'] or 0.00
    total_amount_paid=Invoice.objects.all().aggregate(total_sum=(Sum('amount_paid')))['total_sum'] or 0.00
    total_amount_due = Customer.objects.filter(wallet__lt=0).aggregate(total_sum=Sum('wallet'))['total_sum'] or 0.0
    total_amount_due = abs(total_amount_due)
    print("due amount",total_amount_due)

    stocks = Product.objects.filter(stock__gt=0).count()
    return render(request,'dashboard.html',locals())


def error_page(request,exception):
    return render(request,"404.html",status=404)


@user_passes_test(lambda u:u.is_authenticated and u.is_superuser,login_url='login_page' )
def staff(request):
  users = User.objects.exclude(is_superuser=True).order_by('-id')
  if request.method == "GET":
    search = request.GET.get("search")
    date = request.GET.get("date")
    users = User.objects.exclude(is_superuser=True).order_by('-id')
    if search:
      keyword = search.lower()
      if keyword == "staff":
        users = User.objects.filter(is_staff=True).exclude(is_superuser=True)
      else:
        users = User.objects.filter(
          Q(first_name__icontains=search) |
          Q(id__icontains=search) |
          Q(email__icontains=search)
        ).exclude(is_superuser=True)
    elif date:
      users = User.objects.filter(Q(date_joined__date=date) | Q(last_login__date=date))
    else:
      users = User.objects.exclude(is_superuser=True).order_by('-id')

  return render(request, "staff.html", locals())


@login_required
def activate_staff(request, id):
  user = User.objects.get(id=id)
  if user.is_staff:
    user.is_staff = False
    user.save()
    return redirect('staff')
  else:
    user.is_staff = True
    user.save()
  return redirect('staff')

@login_required
def add_staff(request):
    if request.method == "POST":
        f_name = request.POST.get("f_name")
        l_name = request.POST.get("l_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        image = request.FILES.get("image")
        if User.objects.filter(username=email).exists():
            messages.error(request, "A user with this email already exists!")
            return redirect('add_staff')
        user = User.objects.create(
            username=email,
            first_name=f_name,
            last_name=l_name,
            email=email,
            is_staff=True
        )
        user.set_password(password)
        user.save()

        user_profile = UserProfile.objects.create(
            user=user,
            address=address,
            phone=phone,
        )
        if image:
            user_profile.image = image
        user_profile.save()
        messages.success(request, "Staff added successfully!")
        return redirect('staff')
    return render(request, "add_staff.html")

@login_required
def update_staff(request, id):
  user = get_object_or_404(User, id=id)
  user_profile = get_object_or_404(UserProfile, user_id=id)
  if request.method == "POST":
    user.first_name = request.POST.get("f_name")
    user.last_name = request.POST.get("l_name")
    user.email = request.POST.get("email")
    new_password = request.POST.get("password")
    user_profile.address = request.POST.get("address")
    user_profile.phone = request.POST.get("phone")
    new_image = request.FILES.get("image")
    if new_password:
      user.set_password(new_password)
    if new_image:
      user_profile.image = new_image
    user.save()
    user_profile.save()
    messages.success(request, "Staff Updated Successfully")
    return redirect('staff')
  return render(request, "update_staff.html", locals())


@login_required
def delete_staff(request, id):
  user = User.objects.get(id=id)
  print(user)
  user.delete()
  return redirect(staff)


@login_required
def view_staff(request, id):
  user = User.objects.get(id=id)
  user_profile = get_object_or_404(UserProfile, user=user)
  return render(request, "view_staff.html", locals())


@login_required
def products_list(request):
  if request.method == "GET":
    search = request.GET.get("search")
    print(search)
    if search:
      products = Product.objects.filter(
        Q(name__icontains=search) |
        Q(category__icontains=search) |
        Q(product_id__icontains=search))
    else:
      products = Product.objects.all().order_by('-product_id')
  return render(request, "products.html", locals())

@login_required
def product_view(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, "product_view.html", {"product": product})

@login_required
def add_product(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        name = request.POST.get("name")
        price = request.POST.get("price")
        category = request.POST.get("category")
        stock = request.POST.get("stock")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        if int(stock) < 0:
          messages.warning(request, "Stock can't be less than zero")
          return redirect('add_product')

        product = Product.objects.filter(product_id=product_id)
        if product:
          messages.warning(request, "Already have product with this id!")
          return redirect('add_product')
        else:
          product = Product.objects.create(
            product_id=product_id,
            name=name,
            price=price,
            category=category,
            stock=stock,
            description=description,
          )
          if image:
            product.image = image
            product.save()
          messages.success(request, "Product added succesfully!")
          return redirect('products_list')
    return render(request, "add_product.html", locals())

@login_required
def update_product(request, id):
  product = Product.objects.get(id=id)
  if request.method == "POST":
    product.name = request.POST.get("name")
    product.price = request.POST.get("price")
    product.category = request.POST.get("category")
    stock = request.POST.get("stock")
    product.description = request.POST.get("description")
    if int(stock) < 0:
      messages.warning(request, "Product can't be less than  zero")
      return redirect('update_product', id=id)
    product.stock = stock

    new_image = request.FILES.get("image")
    if new_image:
      product.image = new_image

    product.save()
    messages.success(request, "Product updated successfully")
    return redirect('product_view', id=id)
  return render(request, "update_product.html", locals())



def search_product(request):
    q = request.GET.get('q', '')
    if q:
        products = Product.objects.filter(name__icontains=q,stock__gt=0).values('id', 'name')[:10]
        return JsonResponse(list(products), safe=False)
    return JsonResponse([], safe=False)


@login_required
def customers(request):
  customers = Customer.objects.all().order_by('-id')
  if request.method == "GET":
    search = request.GET.get("search")
    customer = Customer.objects.all().order_by('-id')
    if search:
      customers = Customer.objects.filter(
        Q(fullname__icontains=search) | Q(id__icontains=search) | Q(phone__icontains=search))

    else:
      customers = Customer.objects.all().order_by('-id')
  return render(request, "customers.html", locals())


@login_required
def del_product(request, id):
  product = get_object_or_404(Product, id=id)
  product.delete()
  messages.success(request, "Product deleted successfully.")
  return redirect('products_list')

@login_required
def invoices(request):
    if 'phone' in request.session:
        del request.session['phone']

    search = request.GET.get("search", "")
    date = request.GET.get("date", "")
    status = request.GET.get("status", "")

    invoices = Invoice.objects.all()

    # 🔍 Search
    if search:
        invoices = invoices.filter(
            Q(customer__fullname__icontains=search) |
            Q(id__icontains=search) |
            Q(grand_total__icontains=search)
        )

    # 📅 Date filter
    if date:
        invoices = invoices.filter(date__date=date)

    # ✅ Status filter
    if status == "paid":
        invoices = invoices.filter(amount_paid__gte=F('grand_total'))
    elif status == "pending":
        invoices = invoices.filter(amount_paid__lt=F('grand_total'))

    invoices = invoices.order_by('-id')

    return render(request, "invoices.html", {
        "invoices": invoices,
        "search": search,
        "date": date,
        "status": status
    })


@login_required
def invoice_view(request, id):
  invoice = get_object_or_404(Invoice, id=id)
  invoice_items = InvoiceItem.objects.filter(invoice=invoice)

  wallet = invoice.customer.wallet
  due = 0
  balance = 0
  if wallet < 0:
    due = abs(wallet)
  elif wallet > 0:
    balance = wallet

  return render(request, 'invoice_view.html', {
    'invoice': invoice,
    'invoice_items': invoice_items,
    'due': due,
    'balance': balance
  })



def search_product(request):
  q = request.GET.get('q', '')
  if q:
    products = Product.objects.filter(name__icontains=q, stock__gt=0).values('id', 'name')[:10]
    return JsonResponse(list(products), safe=False)
  return JsonResponse([], safe=False)

def update_cart_totals(cart):
    """Recalculate and update cart totals."""
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.sub_total for item in cart_items)
    gst_percentage = cart.gst_percentage
    gst = (gst_percentage / 100) * total
    grand_total = total + gst

    cart.total = total
    cart.gst = gst
    cart.grand_total = grand_total
    cart.save()


@login_required
@require_POST
def add_to_cart(request, id):
    phone = request.session.get('phone')
    customer = Customer.objects.filter(phone=phone).first()
    if not phone:
        return JsonResponse({"success": False, "message": "Customer not selected"}, status=400)

    customer = get_object_or_404(Customer, phone=phone)
    product = get_object_or_404(Product, id=id)

    # ✅ Ensure Cart exists
    cart, created = Cart.objects.get_or_create(
        customer=customer,
        defaults={
          'gst_percentage': Decimal('2.00'),
          'total': Decimal('0.00'),
          'gst': Decimal('0.00'),
          'grand_total': Decimal('0.00'),
          'amount_paid': Decimal('0.00')
        }
    )

    # ✅ Check stock before adding
    cart_item, created = CartItem.objects.get_or_create(
      cart=cart,
      product=product,
      defaults={
        'quantity': 1,
        'sub_total': product.price  # Ensure `price` is Decimal in model
      }
    )

    if not created:
        if cart_item.quantity + 1 > product.stock:
            return JsonResponse({
                "success": False,
                "message": f"Only {product.stock} items available."
            }, status=400)

        cart_item.quantity += 1
        cart_item.sub_total = product.price * cart_item.quantity
        cart_item.save()

    # ✅ Update Cart totals

    total = sum(Decimal(item.sub_total) for item in CartItem.objects.filter(cart=cart))
    gst = (total * cart.gst_percentage) / Decimal('100')
    cart.total = total
    cart.gst = gst
    cart.grand_total = total + gst
    cart.save()

    print("Session Phone:", request.session.get("phone"))

    return JsonResponse({"success": True, "message": f"{product.name} added successfully."})


# ---------------- Create Invoice ----------------
@login_required
def create_invoice(request):
    if request.method == "POST" and request.content_type == "application/json":
        data = json.loads(request.body)
        phone = data.get("phone")
        if phone:
            request.session["phone"] = phone
            return redirect("create_invoice")

    # ✅ Get customer and cart
    phone = request.session.get("phone")
    customer = None
    cart = None
    due_amount = balance = Decimal(0)

    if phone:
        customer = Customer.objects.filter(phone=phone).first()
        if customer:
            cart, _ = Cart.objects.get_or_create(customer=customer)
            paid = Decimal(cart.amount_paid or 0)
            due_amount = max(Decimal(cart.grand_total or 0) - paid, Decimal(0))
            balance = max(paid - Decimal(cart.grand_total or 0), Decimal(0))

    # ✅ Handle POST actions
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_quantity":
            item_id = int(request.POST.get("item_id"))
            quantity = int(request.POST.get("quantity"))
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            product_stock = int(cart_item.product.stock)

            if 1 <= quantity <= product_stock:
                update_cart_quantity(cart, cart_item, quantity)
            else:
                adjust_quantity_with_stock(request, cart, cart_item, product_stock)

            return redirect("create_invoice")

        elif action == "remove_product":
            item_id = int(request.POST.get("product_id"))
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            cart.total -= cart_item.sub_total
            cart_item.delete()
            recalculate_cart(cart)
            messages.success(request, "Product removed.")
            return redirect("create_invoice")

        elif action == "payment":
            amount_paid = Decimal(request.POST.get("amount_paid", "0"))
            payment_method = request.POST.get("payment_method", "cash")
            if cart and cart.cart_items.exists():
                cart.amount_paid = amount_paid
                cart.payment_method = payment_method
                cart.amount_due = max(cart.grand_total - amount_paid, Decimal(0))
                cart.save()
                messages.success(request, f"Payment recorded: ₹{amount_paid} via {payment_method}")
            else:
                messages.error(request, "No items in cart.")
            return redirect("create_invoice")

        elif action == "save_invoice":
            if not customer:
                messages.error(request, "Add a customer first.")
                return redirect("create_invoice")
            if not cart or not cart.cart_items.exists():
                messages.error(request, "Cart is empty.")
                return redirect("create_invoice")

            # ✅ Handle discount and notes
            discount = Decimal(request.POST.get("discount", "0"))
            notes = request.POST.get("notes", "")

            # ✅ Apply discount
            total = cart.total
            if discount > 0:
                discount_amount = (total * discount) / 100
                total -= discount_amount

            # ✅ Calculate GST and grand total
            gst = (total * cart.gst_percentage) / Decimal(100)
            grand_total = total + gst

            invoice = Invoice.objects.create(
                customer=customer,
                staff=request.user,
                date=now(),
                total=total,
                grand_total=grand_total,
                gst=gst,
                gst_percentage=cart.gst_percentage,
                amount_paid=cart.amount_paid,
                notes=notes if hasattr(Invoice, "notes") else "",
                payment_method=getattr(cart, "payment_method", "cash"),
            )

            # ✅ Wallet and due calculation
            amount_paid = Decimal(cart.amount_paid)
            if amount_paid >= grand_total:
                balance = amount_paid - grand_total
                customer.wallet += balance
                invoice.amount_due = 0
                if hasattr(invoice, 'balance'):
                    invoice.balance = balance
            else:
                due_amount = grand_total - amount_paid
                if customer.wallet > 0:
                    wallet_used = min(customer.wallet, due_amount)
                    customer.wallet -= wallet_used
                    due_amount -= wallet_used
                invoice.amount_due = max(due_amount, Decimal(0))
                if hasattr(invoice, 'balance'):
                    invoice.balance = 0

            # ✅ Save invoice items
            for item in cart.cart_items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                    subtotal=item.sub_total
                )
                item.product.stock -= item.quantity
                item.product.save()

            invoice.save()
            customer.save()

            # ✅ Clear cart (cascade deletes items)
            cart.delete()

            messages.success(request, "Invoice created successfully!")
            return redirect("invoices")

        elif action == "clear_invoice":
            if cart:
                cart.delete()
                request.session.pop("phone", None)
                messages.success(request, "Invoice cleared.")
            else:
                messages.error(request, "No invoice to clear.")
            return redirect("create_invoice")

    cart_items = cart.cart_items.all() if cart else []
    return render(request, "create_invoice.html", {
        "customer": customer,
        "cart": cart,
        "cart_items": cart_items,
        "due_amount": due_amount,
        "balance": balance,
    })


@login_required
def update_invoice_status(request, id):
  invoice = get_object_or_404(Invoice, id=id)

  if request.method == "POST":
    status = request.POST.get("status")
    if status == "paid":
      invoice.amount_paid = invoice.grand_total
      invoice.amount_due = 0
    else:
      invoice.amount_paid = 0
      invoice.amount_due = invoice.grand_total
    invoice.save()
    messages.success(request, "Invoice status updated successfully!")

  return redirect('invoices')


# ----------------- Helper functions -----------------

def update_cart_quantity(cart, cart_item, quantity):
    cart.total -= cart_item.sub_total
    cart_item.quantity = quantity
    cart_item.sub_total = cart_item.product.price * quantity
    cart_item.save()

    cart.total = sum(item.sub_total for item in cart.cart_items.all())
    cart.gst = cart.total * Decimal(cart.gst_percentage / 100)
    cart.grand_total = cart.total + cart.gst
    cart.save()

def adjust_quantity_with_stock(request, cart, cart_item, product_stock):
    messages.warning(request, f"Max stock is {product_stock}. Quantity adjusted.")
    update_cart_quantity(cart, cart_item, max(product_stock, 1))

def recalculate_cart(cart):
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.sub_total for item in cart_items)
    gst = (total * cart.gst_percentage) / Decimal(100)

    cart.total = total
    cart.gst = gst
    cart.grand_total = total + gst
    cart.save()


@login_required
def new_customer(request):
  if request.method == "POST":
    fullname = request.POST.get("fullname")
    phone = request.POST.get("phone")
    address = request.POST.get("address")

    customer = Customer.objects.filter(phone=phone)
    if not customer:
      Customer.objects.create(
        fullname=fullname,
        phone=phone,
        address=address
      )

      request.session['phone'] = phone
      request.session.modified = True

      messages.success(request, "New Customer Added Successfully")
      return redirect('create_invoice')
    else:
      messages.warning(request, "Already have customer with this number")
      return redirect('create_invoice')

  return redirect('create_invoice')


@login_required
def search_customer(request):
  q = request.GET.get('q', '')
  customer = Customer.objects.filter(phone__icontains=q).values('id', 'fullname', 'phone')[:10]
  return JsonResponse(list(customer), safe=False)


def render_to_pdf(html_page, context):
  template = get_template(html_page)
  html = template.render(context)
  response = HttpResponse(content_type='application/pdf')
  response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
  pisa_status = pisa.CreatePDF(html, dest=response)

  return response if not pisa_status.err else HttpResponse('Error creating pdf')


def invoice_pdf(request, id):
  invoice = get_object_or_404(Invoice, id=id)
  invoice_items = InvoiceItem.objects.filter(invoice=invoice)

  # ✅ Fix placement of subtotal calculation
  for item in invoice_items:
    if not item.subtotal or item.subtotal == 0:
      item.subtotal = item.quantity * item.price  # updated only in memory

  wallet = invoice.customer.wallet
  total_balance = wallet if wallet > 0 else 0
  total_due = abs(wallet) if wallet < 0 else 0

  context = {
    'invoice': invoice,
    'invoice_item': invoice_items,
    'total_due': total_due,
    'total_balance': total_balance,
    'wallet': wallet
  }

  template = get_template("invoice_pdf.html")
  html = template.render(context)

  response = HttpResponse(content_type="application/pdf")
  response["Content-Disposition"] = f'inline; filename="invoice_{invoice.id}.pdf"'

  pisa_status = pisa.CreatePDF(html, dest=response)

  if pisa_status.err:
    return HttpResponse("Error generating PDF", status=500)

  return response


def edit_wallet(request, id):
  customer = Customer.objects.get(id=id)
  invoices = Invoice.objects.filter(customer=customer, amount_due__lt=0).order_by('date')
  print(invoices)
  old_wallet = abs(customer.wallet)
  new_balance = 0
  new_due = 0

  if request.method == "POST":
    payment = request.POST.get("payment")
    print(payment)

    customer.wallet += Decimal(payment)

    if customer.wallet >= 0:
      for invoice in invoices:
        invoice.amount_due = 0
        invoice.save()
    else:
      for invoice in invoices:
        payment = Decimal(payment)
        if payment >= abs(invoice.amount_due):
          invoice.amount_due = 0
          payment -= abs(invoice.amount_due)
        else:
          invoice.amount_due += Decimal(payment)
        invoice.save()

    customer.save()
    print(customer.wallet)

    if customer.wallet > 0:
      new_balance = customer.wallet
    elif customer.wallet < 0:
      new_due = abs(customer.wallet)
    else:
      new_balance = 0.00
      new_due = 0.00

    return render(request, 'edit_wallet.html', locals())
  return render(request, "edit_wallet.html", locals())