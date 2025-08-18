from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from django.core.validators import RegexValidator


# ---------------- Product ----------------
CATEGORY_CHOICES = [
    ('Electronics', 'Electronics'),
    ('Clothing', 'Clothing'),
    ('Grocery', 'Grocery'),
]


class Product(models.Model):
    product_id = models.CharField(max_length=10, null=True, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ---------------- Staff Profile ----------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?\d{10,15}$', "Enter a valid phone number")]
    )
    address = models.TextField()
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.user.username


# ---------------- Customer ----------------
class Customer(models.Model):
    fullname = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^\+?\d{10,15}$', "Enter a valid phone number")]
    )
    address = models.TextField()
    wallet = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))

    def __str__(self):
        return self.fullname


# ---------------- Cart ----------------
class Cart(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst_percentage = models.IntegerField(default=2)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Cart No: {self.id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def calculated_sub_total(self):
        return self.quantity * self.product.price

    def save(self, *args, **kwargs):
        self.sub_total = self.calculated_sub_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cart {self.cart.id}"


# ---------------- Invoice ----------------
class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    staff = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    gst_percentage = models.IntegerField(default=2)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    notes = models.TextField(blank=True, null=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('upi', 'UPI'),
            ('bank_transfer', 'Bank Transfer'),
        ],
        default='cash'
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def recalc_totals(self):
        items = self.invoiceitem_set.all()
        self.total = sum(item.subtotal for item in items)
        self.gst = (self.total * Decimal(self.gst_percentage)) / 100
        self.grand_total = self.total + self.gst
        self.amount_due = max(self.grand_total - self.amount_paid, Decimal(0))

        # auto update status
        if self.amount_paid == 0:
            self.status = "pending"
        elif self.amount_paid < self.grand_total:
            self.status = "partial"
        else:
            self.status = "paid"

        self.save()

    def __str__(self):
        return f"Invoice {self.id} ({self.status})"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(self.quantity) * Decimal(self.price)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice.id} - {self.product.name}"
