from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

# Create your models here.
CATEGORY_CHOICES = [
    ('Electronics', 'Electronics'),
    ('Clothing', 'Clothing'),
    ('Grocery', 'Grocery'),
]

class Product(models.Model):
    name = models.CharField(max_length=255)
    product_id = models.CharField(max_length=50, null=True, blank=True)
    description = models.CharField(max_length=225, null=True, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to='images/')
    price = models.DecimalField(decimal_places=2, max_digits=7, null=True, blank=True)
    stock = models.PositiveIntegerField()
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10)
    address = models.TextField()
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.user.username


class Customer(models.Model):
    fullname=models.CharField(max_length=255)
    phone=models.IntegerField(unique=True)
    address=models.TextField()
    wallet=models.DecimalField(max_digits=10,decimal_places=2,default=0.00)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))

    def __str__(self):
        return self.fullname

class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    staff = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    gst_percentage = models.IntegerField(default=2)
    gst = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, default=0, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Invoice {self.id}"


# class InvoiceItem(models.Model):
#     invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField(default=1)
#     sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#
#     def __str__(self):
#         return f"Invoice: {self.invoice}"
#
#
# class Cart(models.Model):
#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     gst_percentage = models.IntegerField(default=2)
#     gst = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
#     grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#
#     def __str__(self):
#         return f"Cart No: {self.id}"
#
#
# class CartItem(models.Model):
#     cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveBigIntegerField(default=1)
#     sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"Cart {self.cart.id}"