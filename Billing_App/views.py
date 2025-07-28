from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Product, UserProfile
from django.template.loader import get_template
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
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
    user = get_object_or_404(User, id=id)  # Get the staff user
    user_profile = get_object_or_404(UserProfile, user=user)  # Get related profile
    return render(request, "view_staff.html", {
        "user": user,
        "user_profile": user_profile
    })


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

@login_required
def del_product(request, id):
      product = Product.objects.get(id=id)
      product.delete()
      return redirect('products_list')

@login_required
def customers(request):
  customer = Customer.objects.all().order_by('-id')
  if request.method == "GET":
    search = request.GET.get("search")
    customer = Customer.objects.all().order_by('-id')
    if search:
      customer = Customer.objects.filter(
        Q(fullname__icontains=search) | Q(id__icontains=search) | Q(phone__icontains=search))
    else:
      customer = Customer.objects.all().order_by('-id')
  return render(request, "customers.html", locals())

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


def invoice(request):
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
  return render(request, "invoice.html", locals())

  import json
  from django.http import JsonResponse
  from django.views.decorators.csrf import csrf_exempt

  def search_product(request):
    q = request.GET.get('q', '')
    if q:
      products = Product.objects.filter(name__icontains=q, stock__gt=0).values('id', 'name')[:10]
      return JsonResponse(list(products), safe=False)
    return JsonResponse([], safe=False)

  @login_required
  def add_product_to_cart(request, id):
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