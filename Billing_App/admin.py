from django.contrib import admin
from . models import *
# Register your models here.

admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Invoice)
# admin.site.register(InvoiceItem)
# admin.site.register(Cart)
# admin.site.register(CartItem)
admin.site.register(UserProfile)