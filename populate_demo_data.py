import random
from django.contrib.auth.models import User
from Billing_App.models import Customer, Product, Invoice, Cart, CartItem
from django.utils.timezone import now
from decimal import Decimal

# --- USERS ---
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")

for i in range(1, 4):
    username = f"staff{i}"
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username=username, password="staff123")

print("✅ Users created/verified")

# --- CUSTOMERS ---
customer_names = [
    "Rahul Sharma", "Priya Verma", "Amit Singh", "Neha Gupta", "Arjun Reddy",
    "Kavya Menon", "Suresh Kumar", "Meena Iyer", "Deepak Joshi", "Alok Nair",
    "Anjali Patel", "Vikram Rao", "Sonia Das", "Rohit Malhotra", "Kiran Bedi",
]

for name in customer_names:
    phone = f"9{random.randint(100000000, 999999999)}"
    address = f"House {random.randint(1,200)}, Street {random.randint(1,20)}, City XYZ"
    Customer.objects.get_or_create(fullname=name, phone=phone, address=address)

print("✅ Customers created")

# --- PRODUCTS ---
products = [
    ("Laptop", 55000), ("Smartphone", 18000), ("Headphones", 1200),
    ("Keyboard", 800), ("Mouse", 500), ("Printer", 8500),
    ("Refrigerator", 32000), ("Television", 40000), ("Washing Machine", 25000),
    ("Mixer Grinder", 3500), ("Ceiling Fan", 2200), ("Water Purifier", 9000),
]

for pname, price in products:
    Product.objects.get_or_create(name=pname, price=Decimal(price))

print("✅ Products created")

# --- INVOICES with CART ---
customers = list(Customer.objects.all())
products = list(Product.objects.all())

for i in range(1, 11):  # 10 invoices
    cust = random.choice(customers)
    cart = Cart.objects.create()
    total = Decimal(0)

    for _ in range(random.randint(1, 3)):
        prod = random.choice(products)
        qty = random.randint(1, 5)
        subtotal = prod.price * qty
        CartItem.objects.create(cart=cart, product=prod, quantity=qty, price=prod.price, subtotal=subtotal)
        total += subtotal

    invoice = Invoice.objects.create(
        cart=cart,
        customer=cust,
        created_at=now(),
        grand_total=total,
        amount_paid=total - Decimal(random.randint(0, 500)),
        amount_due=Decimal(random.randint(0, 500))
    )

print("✅ Invoices with cart items created")

print("🎉 Database populated with demo data successfully!")
