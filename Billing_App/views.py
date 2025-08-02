from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
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
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from .models import Customer, Product, Cart, CartItem, InvoiceItem
from decimal import Decimal
from .models import Invoice
from django.db.models import CharField
from django.views.decorators.csrf import csrf_exempt
from .models import *


# Create your views here.
def index(request):
  return render(request,'index.html')

def login_page(request):
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


@login_required
def dashboard(request):
  return render(request, 'dashboard.html')

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
    if request.method == "GET":
      search = request.GET.get("search")
      date = request.GET.get("date")
      invoices = Invoice.objects.all().order_by('-id')
      if search:
        invoices = Invoice.objects.filter(
          Q(customer__fullname__icontains=search) | Q(id__icontains=search) | Q(grand_total__icontains=search))

      elif date:
        invoices = Invoice.objects.filter(date__date=date)

      else:
        invoices = Invoice.objects.all().order_by('-id')
    return render(request, "invoices.html", locals())


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


# @login_required
# def del_product(request, id):
#     try:
#         cart_item = CartItem.objects.get(id=id)
#         cart_item.delete()
#         messages.success(request, "Product removed from cart.")
#     except CartItem.DoesNotExist:
#         messages.error(request, "Item not found in cart.")
#     return redirect('create_invoice')


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

def add_to_cart(request,id):
  phone = request.session.get('phone')
  if not phone:
    messages.error(request, "Customer phone number missing in session.")
    return redirect('create_invoice')

  customer = Customer.objects.filter(phone=phone).first()
  if not customer:
    messages.error(request, "Customer not found.")
    return redirect('create_invoice')

  cart, created = Cart.objects.get_or_create(customer=customer)

  product = get_object_or_404(Product, id=id, stock__gt=0)
  cart_item = CartItem.objects.filter(cart=cart, product=product).first()
  if cart_item:
    if cart_item.quantity < product.stock:
      cart.total -= cart_item.sub_total
      cart_item.quantity += 1
      cart_item.sub_total = product.price * cart_item.quantity
      cart_item.save()
      cart.total += cart_item.sub_total
    else:
      messages.warning(request, f"Only {product.stock} items available.")
      return redirect("create_invoice")
  else:
    cart_item = CartItem.objects.create(product=product, cart=cart)
    cart_item.sub_total = product.price * cart_item.quantity
    cart_item.save()
    cart.total += cart_item.sub_total

  # Update totals
  gst = cart.total * Decimal(cart.gst_percentage / 100)
  cart.gst = gst
  cart.grand_total = cart.total + cart.gst
  cart.save()

  return redirect("create_invoice")


# ---------------- Create Invoice ----------------
@login_required
def create_invoice(request):
  # ✅ Handle AJAX phone storage
  if request.method == "POST" and request.content_type == "application/json":
    try:
      data = json.loads(request.body)
      phone = data.get('phone')
      if phone:
        request.session['phone'] = phone
        return JsonResponse({'status': 'ok', 'stored_phone': phone})
      else:
        return JsonResponse({'error': 'No phone provided'}, status=400)
    except Exception as e:
      return JsonResponse({'error': str(e)}, status=400)

  # ✅ Retrieve or create customer/cart
  phone = request.session.get("phone")
  customers = Customer.objects.all()
  cart = None
  balance = 0
  due_amount = 0
  amount_paid = 0
  new_wallet_balance = 0
  products = Product.objects.filter(stock__gt=0)

  if phone:
    customer, _ = Customer.objects.get_or_create(
      phone=phone,
      defaults={
        "fullname": "New Customer",
        "address": "",
        "wallet": 0,
        "credit_limit": 0,
      }
    )
    cart, _ = Cart.objects.get_or_create(customer=customer)

  if cart:
    due = cart.amount_due
    due_amount = abs(due) if due < 0 else 0
    balance = due if due >= 0 else 0

  # ✅ Handle actions
  if request.method == "POST":
    action = request.POST.get("action")

    # --- Update quantity ---
    if action == "update_quantity":
      item_id = int(request.POST.get("item_id"))
      quantity = int(request.POST.get("quantity"))
      cart_item = get_object_or_404(CartItem, id=item_id)
      product_stock = int(cart_item.product.stock)

      if 1 <= quantity <= product_stock:
        update_cart_quantity(cart, cart_item, quantity)
      else:
        adjust_quantity_with_stock(cart, cart_item, product_stock)

      return redirect('create_invoice')

    # --- Remove product ---
    elif action == "remove_product":
      item_id = int(request.POST.get("product_id"))
      cart_item = get_object_or_404(CartItem, id=item_id)

      cart.total -= cart_item.sub_total
      cart.gst = cart.total * Decimal((cart.gst_percentage / 100))
      cart.grand_total = cart.total + cart.gst
      cart_item.delete()
      cart.save()

      return redirect('create_invoice')

    # --- Payment ---
    elif action == "payment":
      amount_paid = Decimal(request.POST.get("amount_paid", 0))
      if cart and cart.cartitem_set.exists():
        grand_total = cart.grand_total
        cart.amount_paid = amount_paid
        cart.amount_due = amount_paid - grand_total
        cart.save()

        messages.success(request, f"Payment recorded. Paid: ₹{amount_paid}, Due: ₹{cart.amount_due}")
      else:
        messages.error(request, "No items in cart.")
      return redirect('create_invoice')

    # --- Save invoice ---
    elif action == "save_invoice":
      if not phone:
        messages.error(request, "Add a customer first.")
        return redirect('create_invoice')

      if not cart or not cart.cartitem_set.exists():
        messages.error(request, "Cart is empty.")
        return redirect('create_invoice')

      cart.amount_due = cart.amount_paid - cart.grand_total
      customer = cart.customer
      new_wallet_balance = customer.wallet - abs(cart.amount_due)

      if new_wallet_balance < -customer.credit_limit:
        messages.error(request, f"Credit limit ₹{customer.credit_limit} exceeded.")
        return redirect('create_invoice')

      # ✅ Create invoice
      invoice = Invoice.objects.create(
        customer=customer,
        staff=request.user,
        date=datetime.now(),
        total=cart.total,
        grand_total=cart.grand_total,
        gst=cart.gst,
        amount_paid=cart.amount_paid,
      )
      invoice.amount_due = invoice.amount_paid - invoice.grand_total

      # ✅ Handle wallet balance
      handle_wallet_and_old_dues(customer, invoice)

      # ✅ Save items (with price & subtotal)
      for item in cart.cartitem_set.all():
        InvoiceItem.objects.create(
          invoice=invoice,
          product=item.product,
          quantity=item.quantity,
          price=item.product.price,  # ✅ Added
          subtotal=item.sub_total  # ✅ Added
        )
        item.product.stock -= item.quantity
        item.product.save()

      invoice.save()
      customer.save()

      # ✅ Clear cart
      cart.cartitem_set.all().delete()
      cart.delete()

      messages.success(request, "Invoice created successfully!")
      return redirect('invoices')

    # --- Clear invoice ---
    elif action == "clear_invoice":
      if cart:
        cart.delete()
        request.session.pop('phone', None)
        messages.success(request, "Invoice cleared.")
      else:
        messages.error(request, "No invoice to clear.")
      return redirect('create_invoice')

  cart_items = CartItem.objects.filter(cart=cart).order_by('-created_at')
  return render(request, "create_invoice.html", locals())


# ----------------- Helper functions -----------------

def update_cart_quantity(cart, cart_item, quantity):
  cart.total -= cart_item.sub_total
  cart_item.quantity = quantity
  cart_item.sub_total = cart_item.product.price * quantity
  cart_item.save()
  cart.total += cart_item.sub_total
  cart.gst = cart.total * Decimal((cart.gst_percentage / 100))
  cart.grand_total = cart.total + cart.gst
  cart.save()


def adjust_quantity_with_stock(cart, cart_item, product_stock):
  messages.warning(None, f"Max stock is {product_stock}. Quantity adjusted.")
  update_cart_quantity(cart, cart_item, product_stock if product_stock > 0 else 1)


def handle_wallet_and_old_dues(customer, invoice):
  if invoice.amount_due < 0:
    if customer.wallet >= abs(invoice.amount_due):
      customer.wallet -= abs(invoice.amount_due)
      invoice.amount_due = 0
    else:
      invoice.amount_due += customer.wallet
      customer.wallet = invoice.amount_due
  elif invoice.amount_due > 0:
    old_dues = Invoice.objects.filter(customer=customer, amount_due__lt=0).exclude(id=invoice.id).order_by('date')
    if old_dues:
      customer.wallet += invoice.amount_due
      for old in old_dues:
        if invoice.amount_due <= 0:
          break
        old_due_abs = abs(old.amount_due)
        if invoice.amount_due >= old_due_abs:
          invoice.amount_due -= old_due_abs
          old.amount_due = 0
        else:
          old.amount_due = old_due_abs + invoice.amount_due
          invoice.amount_due = 0
        old.save()
        invoice.save()
    else:
      customer.wallet += invoice.amount_due

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


@login_required
def invoice_pdf(request, id):
  invoice = Invoice.objects.get(id=id)
  invoice_item = InvoiceItem.objects.filter(invoice=invoice)
  wallet = invoice.customer.wallet
  total_balance = 0
  total_due = 0

  if wallet < 0:
    total_due = abs(wallet)
  elif wallet > 0:
    total_balance = wallet

  context = {
    'invoice': invoice,
    'invoice_item': invoice_item,
    'total_due': total_due,
    'total_balance': total_balance,
    'wallet': wallet
  }
  return render_to_pdf("invoice_pdf.html", context)




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