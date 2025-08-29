from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, F, Sum
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from datetime import datetime
import json
from xhtml2pdf import pisa

from .models import (
    Customer, Product, UserProfile, Cart, CartItem,
    Invoice, InvoiceItem
)


def index(request):
    return render(request, 'index.html')


def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(username=email, password=password)
        if user:
            if user.is_staff:
                login(request, user)
                return redirect('dashboard')
            messages.warning(request, "You are not authorized as staff yet.")
        else:
            if not User.objects.filter(username=email).exists():
                messages.warning(request, "You are not registered yet. Please register.")
                return redirect('register')
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
            username=email,
            email=email,
            first_name=f_name,
            last_name=l_name,
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



@never_cache
@login_required
def dashboard(request):
    context = {
        "invoices": Invoice.objects.count(),
        "customers": Customer.objects.count(),
        "products_count": Product.objects.count(),
        "staffs": User.objects.filter(is_staff=True).count(),
        "total_invoice_amount": Invoice.objects.aggregate(total=Sum('grand_total'))['total'] or 0,
        "total_amount_paid": Invoice.objects.aggregate(total=Sum('amount_paid'))['total'] or 0,
        "total_amount_due": Invoice.objects.aggregate(total=Sum('amount_due'))['total'] or 0,
        "stocks": Product.objects.aggregate(total_stock=Sum('stock'))['total_stock'] or 0,
        "recent_invoice": Invoice.objects.order_by('-id')[:5],
        "products_lt10": Product.objects.filter(stock__lt=10),
    }
    return render(request, "dashboard.html", context)



@user_passes_test(lambda u: u.is_authenticated and u.is_superuser, login_url='login_page')
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
    return render(request, "staff.html", {"users": users})

@login_required
def activate_staff(request, id):
    user = get_object_or_404(User, id=id)
    user.is_staff = not user.is_staff
    user.save()
    return redirect('staff')

@login_required
def add_staff(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if User.objects.filter(username=email).exists():
            messages.error(request, "A user with this email already exists!")
            return redirect('add_staff')
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=request.POST.get("f_name"),
            last_name=request.POST.get("l_name"),
            password=request.POST.get("password"),
            is_staff=True
        )
        user_profile = UserProfile.objects.create(
            user=user,
            address=request.POST.get("address"),
            phone=request.POST.get("phone"),
            image=request.FILES.get("image") or None
        )
        messages.success(request, "Staff added successfully!")
        return redirect('staff')
    return render(request, "add_staff.html")

@login_required
def update_staff(request, id):
    user = get_object_or_404(User, id=id)
    user_profile = get_object_or_404(UserProfile, user=user)
    if request.method == "POST":
        user.first_name = request.POST.get("f_name")
        user.last_name = request.POST.get("l_name")
        user.email = request.POST.get("email")
        password = request.POST.get("password")
        if password:
            user.set_password(password)
        user_profile.address = request.POST.get("address")
        user_profile.phone = request.POST.get("phone")
        image = request.FILES.get("image")
        if image:
            user_profile.image = image
        user.save()
        user_profile.save()
        messages.success(request, "Staff Updated Successfully")
        return redirect('staff')
    return render(request, "update_staff.html", {"user": user, "user_profile": user_profile})

@login_required
def delete_staff(request, id):
    user = get_object_or_404(User, id=id)
    user.delete()
    messages.success(request, "Staff deleted successfully.")
    return redirect('staff')

@login_required
def view_staff(request, id):
    user = get_object_or_404(User, id=id)
    user_profile = get_object_or_404(UserProfile, user=user)
    return render(request, "view_staff.html", {"user": user, "user_profile": user_profile})



@login_required
def products_list(request):
    search = request.GET.get("search", "")
    products = Product.objects.all()
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(category__icontains=search) |
            Q(product_id__icontains=search)
        )
    return render(request, "products.html", {"products": products.order_by('-product_id')})


@login_required
def product_view(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, "product_view.html", {"product": product})


@login_required
def add_product(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        if Product.objects.filter(product_id=product_id).exists():
            messages.warning(request, "Product with this ID already exists!")
            return redirect('add_product')

        stock = int(request.POST.get("stock", 0))
        if stock < 0:
            messages.warning(request, "Stock can't be less than zero")
            return redirect('add_product')

        product = Product.objects.create(
            product_id=product_id,
            name=request.POST.get("name"),
            price=Decimal(request.POST.get("price")),
            category=request.POST.get("category"),
            stock=stock,
            description=request.POST.get("description"),
            image=request.FILES.get("image")
        )
        messages.success(request, "Product added successfully!")
        return redirect('products_list')
    return render(request, "add_product.html")


@login_required
def update_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = Decimal(request.POST.get("price"))
        product.category = request.POST.get("category")
        stock = int(request.POST.get("stock"))
        if stock < 0:
            messages.warning(request, "Stock can't be less than zero")
            return redirect('update_product', id=id)
        product.stock = stock
        product.description = request.POST.get("description")
        if request.FILES.get("image"):
            product.image = request.FILES.get("image")
        product.save()
        messages.success(request, "Product updated successfully")
        return redirect('product_view', id=id)
    return render(request, "update_product.html", {"product": product})


@login_required
def del_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    messages.success(request, "Product deleted successfully")
    return redirect('products_list')


@login_required
def customers(request):
    """Display customers with optional search."""
    search_query = request.GET.get("search", "").strip()
    customers = Customer.objects.all().order_by('-id')

    if search_query:
        customers = customers.filter(
            Q(fullname__icontains=search_query) |
            Q(id__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    context = {
        'customers': customers,
        'search': search_query,
    }

    return render(request, "customers.html", context)


@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        if fullname and phone and address:
            customer.fullname = fullname
            customer.phone = phone
            customer.address = address
            customer.save()
            messages.success(request, f"Customer '{customer.fullname}' updated successfully.")
        else: messages.error(request, "All fields are required.")
    return redirect("customers")



@login_required
def invoices(request):
    search = request.GET.get("search", "").strip()
    date_filter = request.GET.get("date", "").strip()
    status_filter = request.GET.get("status", "").strip()

    invoices = Invoice.objects.all()

    if search:
        invoices = invoices.filter(
            Q(customer__fullname__icontains=search) |
            Q(id__icontains=search) |
            Q(grand_total__icontains=search)
        )

    if date_filter:
        invoices = invoices.filter(date__date=date_filter)

    if status_filter == "paid":
        invoices = invoices.filter(amount_paid__gte=F('grand_total'))
    elif status_filter == "pending":
        invoices = invoices.filter(amount_paid__lt=F('grand_total'))

    invoices = invoices.order_by('-id')

    context = {
        "invoices": invoices,
        "search": search,
        "date": date_filter,
        "status": status_filter
    }
    return render(request, "invoices.html", context)


@login_required
def invoice_view(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    invoice_items = invoice.items.all()
    total_due = max(invoice.grand_total - invoice.amount_paid, 0)
    customer_wallet = invoice.customer.wallet or Decimal(0)
    balance = max(customer_wallet - total_due, 0) if customer_wallet > 0 else 0
    due = total_due - balance if balance > 0 else total_due

    return render(request, "invoice_view.html", {
        "invoice": invoice,
        "invoice_items": invoice_items,
        "due": due,
        "balance": balance
    })


@login_required
@require_POST
def make_payment(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    try:
        payment_amount = Decimal(request.POST.get("payment_amount", "0"))
    except:
        messages.error(request, "Invalid amount entered.")
        return redirect("invoice_view", id=id)

    if payment_amount <= 0:
        messages.error(request, "Payment must be greater than zero.")
    else:
        remaining_due = invoice.grand_total - invoice.amount_paid
        if payment_amount > remaining_due:
            messages.error(request, f"Payment cannot exceed remaining due (₹{remaining_due:.2f}).")
        else:
            invoice.amount_paid += payment_amount
            invoice.amount_due = invoice.grand_total - invoice.amount_paid
            invoice.save()
            messages.success(request, f"Payment of ₹{payment_amount:.2f} recorded successfully.")

    return redirect("invoice_view", id=id)


@login_required
def search_product(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.filter(name__icontains=q)[:10]
    data = [{"id": p.id, "name": p.name, "price": float(p.price)} for p in products]
    return JsonResponse(data, safe=False)


@login_required
def add_to_cart(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        quantity = int(data.get("quantity", 1))
        customer_id = data.get("customer_id")
        product = get_object_or_404(Product, id=product_id)
        customer = get_object_or_404(Customer, id=customer_id)
        cart, _ = Cart.objects.get_or_create(customer=customer)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()
        return JsonResponse({"status": "success"})



def update_cart_totals(cart):
    """Recalculate and update cart totals dynamically."""
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.product.price * item.quantity for item in cart_items)
    gst_percentage = cart.gst_percentage
    gst = (gst_percentage / 100) * total
    grand_total = total + gst

    cart.total = total
    cart.gst = gst
    cart.grand_total = grand_total
    cart.save()




@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity and return recalculated totals"""
    try:
        item = get_object_or_404(CartItem, id=item_id)
        new_qty = int(request.POST.get("quantity", 1))
        if new_qty < 1:
            return JsonResponse({"error": "Quantity must be >= 1"}, status=400)

        # ✅ Update item quantity
        item.quantity = new_qty
        item.save()

        # ✅ Recalculate subtotal for this item
        item_subtotal = item.subtotal  # assuming you have @property subtotal in model

        # ✅ Get cart totals
        cart = item.cart
        total = sum(ci.subtotal for ci in cart.cart_items.all())
        gst_percentage = Decimal(getattr(cart, "gst_percentage", 18))  # default 18%
        gst = (total * gst_percentage / 100).quantize(Decimal("0.01"))
        grand_total = total + gst

        # ✅ Handle payment tracking
        amount_paid = getattr(cart, "amount_paid", Decimal("0.00"))
        due_amount = grand_total - amount_paid

        return JsonResponse({
            "success": True,
            "item_id": item.id,
            "item_subtotal": str(item_subtotal),
            "total": str(total),
            "gst": str(gst),
            "grand_total": str(grand_total),
            "amount_paid": str(amount_paid),
            "due_amount": str(due_amount),
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Customer, Product, Cart, CartItem, Invoice, InvoiceItem

GST_PERCENTAGE = Decimal("2.0")  # fixed 2% GST

@login_required
def create_invoice(request):
    customer = None
    cart = None
    cart_items = []

    # --- Get customer from session ---
    customer_id = request.session.get("customer_id")
    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id)
        cart, _ = Cart.objects.get_or_create(customer=customer, active=True)
        cart_items = cart.cart_items.all()

    # --- Helper function to recalc cart totals ---
    def recalc_cart(cart):
        total = sum(i.subtotal for i in cart.cart_items.all())
        gst = (total * GST_PERCENTAGE / 100).quantize(Decimal("0.01"))
        grand_total = total + gst
        amount_paid = getattr(cart, "amount_paid", Decimal("0.00"))
        amount_due = max(grand_total - amount_paid, Decimal("0.00"))
        balance = max(amount_paid - grand_total, Decimal("0.00"))
        cart.total = total
        cart.gst = gst
        cart.grand_total = grand_total
        cart.amount_due = amount_due
        cart.save()
        return total, gst, grand_total, amount_due, balance

    if request.method == "POST":
        action = request.POST.get("action")

        # --- Select existing customer ---
        if action == "select_customer":
            phone = request.POST.get("phone")
            customer = get_object_or_404(Customer, phone=phone)
            request.session["customer_id"] = customer.id
            messages.success(request, f"Customer {customer.fullname} selected.")
            return redirect("create_invoice")

        # --- Add new customer ---
        elif action == "new_customer":
            fullname = request.POST.get("fullname")
            phone = request.POST.get("phone")
            address = request.POST.get("address")
            if Customer.objects.filter(phone=phone).exists():
                messages.warning(request, "Customer already exists!")
            else:
                customer = Customer.objects.create(fullname=fullname, phone=phone, address=address)
                request.session["customer_id"] = customer.id
                messages.success(request, "New customer added successfully.")
            return redirect("create_invoice")

        # --- Add product to cart ---
        elif action == "add_product":
            product_id = int(request.POST.get("product_id"))
            quantity = int(request.POST.get("quantity", 1))
            product = get_object_or_404(Product, id=product_id)
            if not cart:
                messages.error(request, "Please select a customer first.")
                return redirect("create_invoice")
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            cart_item.quantity = cart_item.quantity + quantity if not created else quantity
            cart_item.subtotal = cart_item.quantity * product.price
            cart_item.save()
            recalc_cart(cart)
            return redirect("create_invoice")

        # --- Update quantity / remove product ---
        elif action == "update_item":
            item_id = int(request.POST.get("item_id"))
            quantity = int(request.POST.get("quantity"))
            item = get_object_or_404(CartItem, id=item_id)
            cart = item.cart

            if quantity < 1:
                item.delete()
            else:
                item.quantity = quantity
                item.subtotal = item.quantity * item.product.price
                item.save()

            # Recalculate totals
            total = sum(i.subtotal for i in cart.cart_items.all())
            gst = (total * GST_PERCENTAGE / 100).quantize(Decimal("0.01"))
            grand_total = total + gst
            amount_paid = getattr(cart, "amount_paid", Decimal("0.00"))
            amount_due = max(grand_total - amount_paid, 0)
            cart.total = total
            cart.gst = gst
            cart.grand_total = grand_total
            cart.amount_due = amount_due
            cart.save()

            return JsonResponse({
                "success": True,
                "subtotal": float(item.subtotal) if quantity > 0 else 0,
                "grand_total": float(cart.grand_total),
                "due_amount": float(cart.amount_due),
                "cart_count": cart.cart_items.count(),
            })
        # --- Record payment ---
        elif action == "payment":
            amount_paid = Decimal(request.POST.get("amount_paid", 0))
            if cart:
                total, gst, grand_total, amount_due, balance = recalc_cart(cart)
                if amount_paid > grand_total:
                    excess = amount_paid - grand_total
                    cart.amount_paid = grand_total
                    cart.amount_due = Decimal("0.00")
                    customer.wallet += excess
                    customer.save()
                    messages.success(request, f"Payment recorded. Excess ₹{excess} added to wallet.")
                elif amount_paid < grand_total:
                    cart.amount_paid = amount_paid
                    cart.amount_due = grand_total - amount_paid
                    messages.success(request, f"Partial payment recorded. Due: ₹{cart.amount_due}")
                else:
                    cart.amount_paid = amount_paid
                    cart.amount_due = Decimal("0.00")
                    messages.success(request, "Payment recorded. No due or balance.")
                cart.save()
            return redirect("create_invoice")

        # --- Apply discount ---
        elif action == "apply_discount":
            discount = Decimal(request.POST.get("discount", 0))
            if cart:
                total, gst, grand_total, amount_due, balance = recalc_cart(cart)
                discount_amount = (grand_total * discount / 100).quantize(Decimal("0.01"))
                cart.grand_total = grand_total - discount_amount
                cart.amount_due = max(cart.grand_total - getattr(cart, "amount_paid", Decimal("0.00")), Decimal("0.00"))
                cart.save()
            return redirect("create_invoice")

        # --- Save invoice ---
        elif action == "save_invoice":
            if not cart or not customer or not cart.cart_items.exists():
                messages.error(request, "Select customer and add products first.")
                return redirect("create_invoice")

            total, gst, grand_total, amount_due, balance = recalc_cart(cart)
            amount_paid = getattr(cart, "amount_paid", Decimal("0.00"))

            # Excess goes to wallet
            if amount_paid > grand_total:
                excess = amount_paid - grand_total
                customer.wallet += excess
                customer.save()
                amount_paid = grand_total

            invoice = Invoice.objects.create(
                customer=customer,
                staff=request.user,
                total=total,
                gst=gst,
                grand_total=grand_total,
                amount_paid=amount_paid,
                amount_due=max(grand_total - amount_paid, 0)
            )

            for item in cart.cart_items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                    subtotal=item.subtotal
                )
                item.product.stock -= item.quantity
                item.product.save()

            # Clear cart
            cart.cart_items.all().delete()
            cart.delete()
            request.session.pop("customer_id", None)

            messages.success(request, f"Invoice {invoice.id} created successfully.")
            return redirect("invoice_view", id=invoice.id)

    # --- Recalculate totals for display ---
    if cart:
        total, gst, grand_total, due_amount, balance = recalc_cart(cart)
    else:
        total = gst = grand_total = due_amount = balance = Decimal("0.00")

    return render(request, "create_invoice.html", {
        "customer": customer,
        "cart": cart,
        "cart_items": cart_items,
        "due_amount": due_amount,
        "balance": balance,
    })



def _item_subtotal(i):
    """Works whether you store subtotal as field or compute property."""
    if hasattr(i, 'subtotal') and i.subtotal is not None:
        return i.subtotal
    if hasattr(i, 'sub_total') and i.sub_total is not None:
        return i.sub_total
    price = getattr(i, 'price', None) or getattr(i.product, 'price', Decimal('0'))
    return (i.quantity or 0) * price





@login_required
def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    customer = invoice.customer
    cart_items = invoice.items.all()  # Use related_name from InvoiceItem

    if request.method == "POST":
        action = request.POST.get("action")

        # Update customer info
        if action == "edit_customer":
            customer.fullname = request.POST.get("fullname", customer.fullname)
            customer.phone = request.POST.get("phone", customer.phone)
            customer.address = request.POST.get("address", customer.address)
            customer.save()
            messages.success(request, "Customer info updated ✅")
            return redirect("edit_invoice", invoice_id=invoice.id)

        # Record payment
        elif action == "payment":
            try:
                amount_paid = Decimal(request.POST.get("amount_paid", 0))
            except:
                amount_paid = Decimal(0)

            invoice.amount_paid += amount_paid
            invoice.amount_due = max(invoice.grand_total - invoice.amount_paid, 0)
            invoice.payment_method = request.POST.get("payment_method", invoice.payment_method)
            invoice.save()
            messages.success(request, f"Payment of ₹{amount_paid} recorded successfully!")
            return redirect("edit_invoice", invoice_id=invoice.id)

        # Save invoice notes
        elif action == "save_invoice":
            invoice.notes = request.POST.get("notes", invoice.notes)
            invoice.save()
            messages.success(request, "Invoice updated successfully!")
            return redirect("invoices")

    return render(request, "edit_invoice.html", {
        "invoice": invoice,
        "customer": customer,
        "cart_items": cart_items,
    })


@login_required
def save_invoice(request):
    if request.method == "POST":
        # Example: create an invoice
        customer_id = request.POST.get("customer_id")  # sent via JS if needed
        customer = Customer.objects.get(id=customer_id) if customer_id else None

        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({"success": False, "message": "Cart is empty"})

        total_amount = sum(item.product.price * item.quantity for item in cart_items)

        invoice = Invoice.objects.create(
            customer=customer,
            date=now(),
            total_amount=total_amount,
        )

        # Optional: save cart items to invoice
        for item in cart_items:
            invoice.items.create(
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
        # Clear cart
        cart_items.delete()

        return JsonResponse({"success": True, "message": "Invoice saved"})

    return JsonResponse({"success": False, "message": "Invalid request"})


@login_required
def delete_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    customer = invoice.customer

    if request.method == "POST":
        # Restore stock
        for item in invoice.items.all():
            item.product.stock += item.quantity
            item.product.save()

        # Refund any overpayment to customer wallet
        overpayment = invoice.amount_paid - invoice.grand_total
        if overpayment > 0:
            customer.wallet += overpayment
            customer.save()

        invoice.delete()
        messages.success(request, "Invoice deleted successfully ❌")
        return redirect("invoices")

    return render(request, "delete_invoice.html", {"invoice": invoice})



@login_required
def clear_invoice(request):
    if request.method == "POST":
        CartItem.objects.filter(user=request.user).delete()  # adjust according to your cart
        return JsonResponse({"success": True, "message": "Cart cleared"})

    return JsonResponse({"success": False, "message": "Invalid request"})


@login_required
def update_payment(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.method == "POST":
        try:
            amount_paid = Decimal(request.POST.get("amount_paid", 0))
        except:
            return JsonResponse({"success": False, "error": "Invalid amount"})
        if amount_paid < 0:
            return JsonResponse({"success": False, "error": "Amount must be >= 0"})

        cart.amount_paid = amount_paid
        cart.amount_due = max(cart.grand_total - cart.amount_paid, 0)
        cart.save()
        return JsonResponse({"success": True, "amount_paid": float(cart.amount_paid), "due_amount": float(cart.amount_due)})
    return JsonResponse({"success": False})



@login_required
def update_invoice_status(request, id):
    invoice = get_object_or_404(Invoice, id=id)

    if request.method == "POST":
        try:
            payment = Decimal(request.POST.get("amount_paid", "0"))
        except:
            messages.error(request, "Invalid payment amount.")
            return redirect("invoice_view", id=id)

        if payment <= 0:
            messages.error(request, "Payment must be greater than zero.")
            return redirect("invoice_view", id=id)

        remaining_due = invoice.grand_total - invoice.amount_paid

        if payment > remaining_due:
            messages.error(request, f"Payment cannot exceed remaining due (₹{remaining_due:.2f}).")
            return redirect("invoice_view", id=id)

        # Apply payment
        invoice.amount_paid += payment
        invoice.amount_due = invoice.grand_total - invoice.amount_paid
        invoice.save()
        messages.success(request, f"Payment of ₹{payment:.2f} recorded successfully ✅")
    return redirect("invoice_view", id=id)

# ----------------- Helper functions -----------------

@login_required
@csrf_exempt
def update_quantity(request):
    if request.method == "POST":
        data = json.loads(request.body)
        item_id = data.get("item_id")
        quantity = int(data.get("quantity", 1))

        cart_item = get_object_or_404(CartItem, id=item_id)
        cart_item.quantity = quantity
        cart_item.subtotal = cart_item.quantity * cart_item.product.price
        cart_item.save()

        # Update cart totals
        cart = cart_item.cart
        cart.total = sum(item.subtotal for item in cart.cart_items.all())
        cart.grand_total = cart.total + (cart.total * cart.gst_percentage / Decimal(100))
        cart.save()

        return JsonResponse({
            "success": True,
            "subtotal": float(cart_item.subtotal),
            "grand_total": float(cart.grand_total)
        })
    return JsonResponse({"success": False, "message": "Invalid request"})



@login_required
@csrf_exempt
def record_payment(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)

    if not cart.customer:
        return JsonResponse({"success": False, "error": "Please select a customer first"})

    if request.method == "POST":
        data = json.loads(request.body)
        amount_paid = Decimal(data.get("amount_paid", "0"))
        payment_method = data.get("payment_method", "cash")

        cart.amount_paid = amount_paid
        cart.payment_method = payment_method
        cart.save()

        gst = cart.total * cart.gst_percentage / 100
        grand_total = cart.total + gst
        due_amount = max(grand_total - cart.amount_paid, 0)
        balance = max(cart.amount_paid - grand_total, 0)

        return JsonResponse({
            "success": True,
            "amount_paid": float(cart.amount_paid),
            "due_amount": float(due_amount),
            "balance": float(balance),
            "payment_method": payment_method,
        })

    return JsonResponse({"success": False, "error": "Invalid request"})



def get_or_create_cart(request):
    cart_id = request.session.get("cart_id")
    if cart_id:
        try:
            return Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            pass
    cart = Cart.objects.create(total=0, gst_percentage=18)
    request.session["cart_id"] = cart.id
    return cart



@csrf_exempt
@login_required
def assign_customer_to_cart(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        customer_id = data.get("customer_id")

        try:
            customer = Customer.objects.get(id=customer_id)
            request.session["phone"] = customer.phone  # store in session
            return JsonResponse({"success": True})
        except Customer.DoesNotExist:
            return JsonResponse({"success": False, "error": "Customer not found"})

    return JsonResponse({"success": False, "error": "Invalid request"})


def adjust_quantity_with_stock(request, cart, cart_item, product_stock):
    messages.warning(request, f"Max stock is {product_stock}. Quantity adjusted.")
    cart_item.quantity = max(min(cart_item.quantity, product_stock), 1)
    cart_item.subtotal = cart_item.quantity * cart_item.product.price
    cart_item.save()
    update_cart_totals(cart)



def _recalc_cart(cart):
    """Recalculate totals on the Cart model."""
    try:
        items = cart.cart_items.all()
    except Exception:
        items = CartItem.objects.filter(cart=cart)
    total = sum(_item_subtotal(i) for i in items)
    gst_pct = getattr(cart, "gst_percentage", Decimal("0")) or Decimal("0")
    gst = (total * gst_pct) / Decimal("100")
    cart.total = total
    cart.gst = gst
    cart.grand_total = total + gst
    paid = getattr(cart, "amount_paid", Decimal("0")) or Decimal("0")
    cart.amount_due = max(cart.grand_total - paid, 0)
    cart.save()


@login_required
def new_customer(request):
    if request.method == "POST":
        fullname = request.POST.get("fullname")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        if Customer.objects.filter(phone=phone).exists():
            messages.warning(request, "Customer with this number already exists")
            return redirect('create_invoice')

        customer = Customer.objects.create(
            fullname=fullname, phone=phone, address=address
        )
        request.session['customer_id'] = customer.id   # ✅ store customer_id
        request.session['phone'] = customer.phone      # optional: keep phone too
        messages.success(request, "New Customer Added Successfully")
        return redirect('create_invoice')
    return redirect('create_invoice')


@login_required
def set_customer(request):
    customer_id = request.GET.get('id')
    if customer_id:
        request.session['customer_id'] = customer_id
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})



@login_required
@csrf_exempt
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == "POST":
        data = json.loads(request.body)
        item.quantity = int(data.get("quantity", item.quantity))
        item.subtotal = item.quantity * item.price
        item.save()

        cart = item.cart
        cart.total = sum(i.subtotal for i in cart.cartitem_set.all())
        cart.save()

        gst = cart.total * cart.gst_percentage / 100
        grand_total = cart.total + gst

        return JsonResponse({
            "success": True,
            "item_subtotal": float(item.subtotal),
            "cart_total": float(cart.total),
            "grand_total": float(grand_total),
        })
    return JsonResponse({"success": False})



@login_required
def search_customer(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        customers = Customer.objects.filter(
            Q(phone__icontains=query) | Q(fullname__icontains=query)
        )[:10]
        results = list(customers.values("fullname", "phone"))
    return JsonResponse(results, safe=False)

# @login_required
# @csrf_exempt
# def set_customer_ajax(request, customer_id):
#     # customer = get_object_or_404(Customer, id=customer_id)
#     request.session["customer_id"] = customer.id
#     return JsonResponse({"success": True})




def render_to_pdf(template_src, context):
    template = get_template(template_src)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response if not pisa_status.err else HttpResponse("Error creating PDF")


@login_required
def invoice_pdf(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)
    wallet = invoice.customer.wallet or Decimal(0)
    total_balance = max(wallet, 0)
    total_due = abs(min(wallet, 0))
    context = {
        'request': request,
        'invoice': invoice,
        'invoice_items': invoice_items,
        'total_balance': total_balance,
        'total_due': total_due,
        'wallet': wallet
    }
    return render_to_pdf("invoice_pdf.html", context)


# ------------------- Wallet -------------------

@login_required
def edit_wallet(request, id):
    customer = get_object_or_404(Customer, id=id)
    invoices = Invoice.objects.filter(customer=customer, amount_due__lt=0).order_by('date')
    old_wallet = customer.wallet
    new_balance, new_due = 0, 0

    if request.method == "POST":
        try:
            payment = Decimal(request.POST.get("payment", "0"))
        except:
            messages.error(request, "Invalid payment amount.")
            return redirect("edit_wallet", id=id)

        customer.wallet += payment
        remaining_payment = payment

        for invoice in invoices:
            if remaining_payment <= 0:
                break
            due_abs = abs(invoice.amount_due)
            applied = min(remaining_payment, due_abs)
            invoice.amount_due += applied
            remaining_payment -= applied
            invoice.save()

        customer.save()
        new_balance = max(customer.wallet, 0)
        new_due = abs(min(customer.wallet, 0))
        messages.success(request, f"Wallet updated. Balance: ₹{new_balance}, Due: ₹{new_due}")

    return render(request, "edit_wallet.html", {
        "customer": customer,
        "invoices": invoices,
        "old_wallet": old_wallet,
        "new_balance": new_balance,
        "new_due": new_due
    })