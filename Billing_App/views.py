from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, F, Sum
from django.template.loader import get_template
from django.http import HttpResponse, JsonResponse
from datetime import datetime
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
from xhtml2pdf import pisa

from .models import (
    Customer, Product, Cart, CartItem,
    Invoice, InvoiceItem, UserProfile
)

# ----------------- Authentication -----------------
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
            if user.is_staff:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.warning(request, "Not authorized as staff. Wait for admin approval.")
        else:
            if not User.objects.filter(username=email).exists():
                messages.warning(request, "You are not registered yet. Please register.")
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
        if User.objects.filter(username=email).exists():
            messages.warning(request, "Email already exists. Please login.")
            return redirect('login_page')

        user = User.objects.create_user(
            username=email, email=email,
            first_name=f_name, last_name=l_name,
            password=password
        )
        messages.success(request, "Account created successfully. Please login.")
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


# ----------------- Dashboard -----------------
@never_cache
@login_required
def dashboard(request):
    invoices = Invoice.objects.all().count()
    customers = Customer.objects.all().count()
    products_count = Product.objects.all().count()
    products_lt10 = Product.objects.filter(stock__lt=5)
    staffs = User.objects.filter(is_staff=True, is_superuser=False).count()

    today = now().date()
    recent_invoice = Invoice.objects.filter(date__date=today).order_by('-id')
    total_invoice_amount = Invoice.objects.aggregate(total_sum=Sum('grand_total'))['total_sum'] or 0
    total_amount_paid = Invoice.objects.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0
    total_amount_due = Customer.objects.filter(wallet__lt=0).aggregate(total_sum=Sum('wallet'))['total_sum'] or 0
    total_amount_due = abs(total_amount_due)

    stocks = Product.objects.filter(stock__gt=0).count()
    return render(request,'dashboard.html',locals())

def error_page(request,exception):
    return render(request,"404.html",status=404)


# ----------------- Staff -----------------
@user_passes_test(lambda u:u.is_authenticated and u.is_superuser, login_url='login_page')
def staff(request):
    users = User.objects.exclude(is_superuser=True).order_by('-id')
    search = request.GET.get("search")
    date = request.GET.get("date")
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
    return render(request, "staff.html", locals())

@login_required
def activate_staff(request, id):
    user = User.objects.get(id=id)
    user.is_staff = not user.is_staff
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
            messages.error(request, "User already exists!")
            return redirect('add_staff')

        user = User.objects.create_user(
            username=email, first_name=f_name,
            last_name=l_name, email=email,
            password=password, is_staff=True
        )
        user_profile = UserProfile.objects.create(
            user=user, address=address, phone=phone, image=image
        )
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
    user = get_object_or_404(User, id=id)
    user.delete()
    messages.success(request, "Staff deleted.")
    return redirect('staff')

@login_required
def view_staff(request, id):
    user = get_object_or_404(User, id=id)
    user_profile = get_object_or_404(UserProfile, user=user)
    return render(request, "view_staff.html", locals())


# ----------------- Products -----------------
@login_required
def products_list(request):
    search = request.GET.get("search")
    if search:
        products = Product.objects.filter(
            Q(name__icontains=search) |
            Q(category__icontains=search) |
            Q(product_id__icontains=search)
        )
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
            messages.warning(request, "Stock can't be negative")
            return redirect('add_product')

        if Product.objects.filter(product_id=product_id).exists():
            messages.warning(request, "Product ID already exists!")
            return redirect('add_product')

        product = Product.objects.create(
            product_id=product_id, name=name, price=price,
            category=category, stock=stock, description=description,
            image=image
        )
        messages.success(request, "Product added successfully!")
        return redirect('products_list')
    return render(request, "add_product.html")


def search_product(request):
    q = request.GET.get('q', '')
    if q:products = Product.objects.filter(name__icontains=q, stock__gt=0).values('id', 'name')[:10]
    return JsonResponse(list(products), safe=False)
    return JsonResponse([], safe=False)

@login_required
def update_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.category = request.POST.get("category")
        stock = int(request.POST.get("stock"))
        product.description = request.POST.get("description")
        if stock < 0:
            messages.warning(request, "Stock can't be negative")
            return redirect('update_product', id=id)
        product.stock = stock
        new_image = request.FILES.get("image")
        if new_image:
            product.image = new_image
        product.save()
        messages.success(request, "Product updated successfully")
        return redirect('product_view', id=id)
    return render(request, "update_product.html", locals())

@login_required
def del_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect('products_list')


# ----------------- Customers -----------------
@login_required
def customers(request):
    customers = Customer.objects.all().order_by('-id')
    search = request.GET.get("search")
    if search:
        customers = Customer.objects.filter(
            Q(fullname__icontains=search) |
            Q(id__icontains=search) |
            Q(phone__icontains=search)
        )
    return render(request, "customers.html", locals())

@login_required
def new_customer(request):
    if request.method == "POST":
        fullname = request.POST.get("fullname")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        if Customer.objects.filter(phone=phone).exists():
            messages.warning(request, "Customer with this number already exists")
            return redirect('create_invoice')

        Customer.objects.create(
            fullname=fullname, phone=phone, address=address
        )
        request.session['phone'] = phone
        messages.success(request, "New Customer Added Successfully")
        return redirect('create_invoice')
    return redirect('create_invoice')

@login_required
def search_customer(request):
    q = request.GET.get('q', '')
    customer = Customer.objects.filter(phone__icontains=q).values('id', 'fullname', 'phone')[:10]
    return JsonResponse(list(customer), safe=False)

@login_required
def edit_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    if request.method == "POST":
        customer.fullname = request.POST.get("fullname")
        customer.phone = request.POST.get("phone")
        customer.address = request.POST.get("address")
        customer.save()
        messages.success(request, "Customer updated successfully.")
        return redirect("customers")
    return render(request, "edit_customer.html", {"customer": customer})


# ----------------- Invoices -----------------
@login_required
def invoices(request):
    if 'phone' in request.session:
        del request.session['phone']

    search = request.GET.get("search", "")
    date = request.GET.get("date", "")
    status = request.GET.get("status", "")

    invoices = Invoice.objects.all()

    if search:
        invoices = invoices.filter(
            Q(customer__fullname__icontains=search) |
            Q(id__icontains=search) |
            Q(grand_total__icontains=search)
        )

    if date:
        invoices = invoices.filter(date__date=date)

    if status == "paid":
        invoices = invoices.filter(amount_paid__gte=F('grand_total'))
    elif status == "pending":
        invoices = invoices.filter(amount_paid__lt=F('grand_total'))

    invoices = invoices.order_by('-id')
    return render(request, "invoices.html", {"invoices": invoices, "search": search, "date": date, "status": status})


@login_required
def invoice_view(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)

    wallet = invoice.customer.wallet
    due = abs(wallet) if wallet < 0 else 0
    balance = wallet if wallet > 0 else 0

    return render(request, 'invoice_view.html', {
        'invoice': invoice,
        'invoice_items': invoice_items,
        'due': due,
        'balance': balance
    })


@login_required
def edit_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    if request.method == "POST":
        notes = request.POST.get("notes", "")
        discount = Decimal(request.POST.get("discount", "0"))
        invoice.notes = notes
        invoice.discount = discount
        invoice.save()
        messages.success(request, "Invoice updated successfully.")
        return redirect("invoice_view", id=id)
    return render(request, "edit_invoice.html", {"invoice": invoice})


@login_required
def delete_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    if request.method == "POST":
        invoice.delete()
        messages.success(request, "Invoice deleted successfully.")
        return redirect("invoices")
    return render(request, "delete_invoice.html", {"invoice": invoice})


# ----------------- Update Invoice Payment -----------------
@login_required
def update_invoice_status(request, id):
    invoice = get_object_or_404(Invoice, id=id)

    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount_paid", "0"))
        except:
            messages.error(request, "Invalid amount entered.")
            return redirect("invoice_view", id=id)

        if amount <= 0:
            messages.error(request, "Payment must be greater than zero.")
            return redirect("invoice_view", id=id)

        if amount > invoice.amount_due:
            messages.error(request, f"Payment cannot exceed due amount (₹{invoice.amount_due}).")
            return redirect("invoice_view", id=id)

        # ✅ Apply partial or full payment
        invoice.amount_paid += amount
        invoice.amount_due = max(invoice.grand_total - invoice.amount_paid, Decimal(0))
        invoice.save()

        # ✅ If overpayment somehow occurs, move extra to wallet
        if invoice.amount_paid > invoice.grand_total:
            extra = invoice.amount_paid - invoice.grand_total
            invoice.customer.wallet += extra
            invoice.amount_due = 0
            invoice.customer.save()
            invoice.save()

        messages.success(request, f"Payment of ₹{amount} recorded successfully.")

    return redirect("invoice_view", id=id)

# ----------------- Cart & Invoice Creation -----------------
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
    if not phone:
        return JsonResponse({"success": False, "message": "Customer not selected"}, status=400)

    customer = get_object_or_404(Customer, phone=phone)
    product = get_object_or_404(Product, id=id)

    # ✅ Ensure Cart exists
    cart, _ = Cart.objects.get_or_create(
        customer=customer,
        defaults={'gst_percentage': 2, 'total': 0, 'gst': 0, 'grand_total': 0, 'amount_paid': 0}
    )

    # ✅ Check stock and add item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={'quantity': 1, 'sub_total': product.price}
    )

    if not created:
        if cart_item.quantity + 1 > product.stock:
            return JsonResponse({"success": False, "message": f"Only {product.stock} items available."}, status=400)
        cart_item.quantity += 1
        cart_item.sub_total = product.price * cart_item.quantity
        cart_item.save()

    update_cart_totals(cart)
    return JsonResponse({"success": True, "message": f"{product.name} added successfully."})


@login_required
def create_invoice(request):
    phone = request.session.get("phone")
    customer = Customer.objects.filter(phone=phone).first() if phone else None
    cart = Cart.objects.filter(customer=customer).first() if customer else None
    due_amount = balance = Decimal(0)

    if cart:
        paid = Decimal(cart.amount_paid or 0)
        due_amount = max(Decimal(cart.grand_total or 0) - paid, Decimal(0))
        balance = max(paid - Decimal(cart.grand_total or 0), Decimal(0))

    if request.method == "POST":
        action = request.POST.get("action")

        # ✅ Update quantity
        if action == "update_quantity":
            item_id = int(request.POST.get("item_id"))
            quantity = int(request.POST.get("quantity"))
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

            if 1 <= quantity <= cart_item.product.stock:
                update_cart_quantity(cart, cart_item, quantity)
            else:
                adjust_quantity_with_stock(request, cart, cart_item, cart_item.product.stock)
            return redirect("create_invoice")

        # ✅ Remove product
        elif action == "remove_product":
            item_id = int(request.POST.get("product_id"))
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            cart_item.delete()
            recalculate_cart(cart)
            messages.success(request, "Product removed.")
            return redirect("create_invoice")

        # ✅ Record payment
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

        # ✅ Save Invoice
        elif action == "save_invoice":
            if not customer:
                messages.error(request, "Add a customer first.")
                return redirect("create_invoice")
            if not cart or not cart.cart_items.exists():
                messages.error(request, "Cart is empty.")
                return redirect("create_invoice")

            discount = Decimal(request.POST.get("discount", "0"))
            notes = request.POST.get("notes", "")

            total = cart.total
            if discount > 0:
                total -= (total * discount) / 100

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
                amount_due=max(grand_total - cart.amount_paid, Decimal(0)),
                notes=notes,
                payment_method=getattr(cart, "payment_method", "cash"),
            )

            for item in cart.cart_items.all():
                InvoiceItem.objects.create(
                    invoice=invoice, product=item.product,
                    quantity=item.quantity, price=item.product.price,
                    subtotal=item.sub_total
                )
                item.product.stock -= item.quantity
                item.product.save()

            invoice.save()
            customer.save()
            cart.delete()

            messages.success(request, "Invoice created successfully!")
            return redirect("invoices")

        # ✅ Clear cart
        elif action == "clear_invoice":
            if cart:
                cart.delete()
                request.session.pop("phone", None)
                messages.success(request, "Invoice cleared.")
            return redirect("create_invoice")

    cart_items = cart.cart_items.all() if cart else []
    return render(request, "create_invoice.html", {
        "customer": customer,
        "cart": cart,
        "cart_items": cart_items,
        "due_amount": due_amount,
        "balance": balance,
    })


# ----------------- Wallet -----------------
@login_required
def edit_wallet(request, id):
    customer = get_object_or_404(Customer, id=id)
    invoices = Invoice.objects.filter(customer=customer, amount_due__gt=0).order_by("date")
    old_wallet = customer.wallet

    if request.method == "POST":
        payment = Decimal(request.POST.get("payment", "0"))
        if payment <= 0:
            messages.error(request, "Invalid payment amount.")
            return redirect("edit_wallet", id=id)

        customer.wallet += payment
        for invoice in invoices:
            if payment <= 0: break
            if invoice.amount_due > 0:
                if payment >= invoice.amount_due:
                    payment -= invoice.amount_due
                    invoice.amount_paid += invoice.amount_due
                    invoice.amount_due = 0
                else:
                    invoice.amount_paid += payment
                    invoice.amount_due -= payment
                    payment = 0
                invoice.save()

        customer.save()
        messages.success(request, "Wallet updated successfully.")
        return redirect("customers")

    return render(request, "edit_wallet.html", {
        "customer": customer,
        "invoices": invoices,
        "old_wallet": old_wallet,
        "new_balance": customer.wallet if customer.wallet > 0 else 0,
        "new_due": abs(customer.wallet) if customer.wallet < 0 else 0,
    })


# ----------------- PDF Export -----------------
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

    for item in invoice_items:
        if not item.subtotal or item.subtotal == 0:
            item.subtotal = item.quantity * item.price

    wallet = invoice.customer.wallet
    total_balance = wallet if wallet > 0 else 0
    total_due = abs(wallet) if wallet < 0 else 0

    context = {"invoice": invoice, "invoice_item": invoice_items,
               "total_due": total_due, "total_balance": total_balance, "wallet": wallet}

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{invoice.id}.pdf"'
    pisa_status = pisa.CreatePDF(get_template("invoice_pdf.html").render(context), dest=response)
    return response if not pisa_status.err else HttpResponse("Error generating PDF", status=500)


# ----------------- Helpers -----------------
def update_cart_quantity(cart, cart_item, quantity):
    cart.total -= cart_item.sub_total
    cart_item.quantity = quantity
    cart_item.sub_total = cart_item.product.price * quantity
    cart_item.save()
    recalculate_cart(cart)

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
