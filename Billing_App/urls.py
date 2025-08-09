from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from Billing_App import views

urlpatterns = [
  path('', views.index, name='index'),
  path('login_page/', auth_views.Login_pageView.as_view(template_name='login.html'), name='login_page'),
  path('logout_page/', auth_views.Logout_pageView.as_view(), name='logout_page'),
  path('dashboard/', views.dashboard, name='dashboard'),
  path('register/', views.register, name='register'),
  path('forgot_password/', views.forgot_password, name='forgot_password'),
  path('staff', views.staff, name='staff'),
  path('activate_staff/<int:id>/', views.activate_staff, name='activate_staff'),
  path('add_staff/', views.add_staff, name='add_staff'),
  path('update_staff/<int:id>/', views.update_staff, name='update_staff'),
  path('delete_staff/<int:id>/', views.delete_staff, name='delete_staff'),
  path('view_staff/<int:id>/', views.view_staff, name='view_staff'),
  path('products', views.products_list, name="products_list"),
  path('view/<int:id>/', views.product_view, name="product_view"),
  path('add_product/', views.add_product, name="add_product"),
  path('update_product/<int:id>/', views.update_product, name="update_product"),
  path('del_product/<int:id>/', views.del_product, name='del_product'),
  path('invoices', views.invoices, name="invoices"),
  path('create_invoice/', views.create_invoice, name='create_invoice'),
  path('customers', views.customers, name="customers"),
  path('new_customer/',views.new_customer,name="new_customer"),
  path('search_customer',views.search_customer,name="search_customer"),
  path('add_to_cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
  path('search_product',views.search_product,name="search_product"),
  # path('invoice_view/<int:id>',views.invoice_view,name="invoice_view"),
  path('invoice/<int:id>/view/', views.invoice_view, name='invoice_view'),
  path('update_invoice_status/<int:id>/', views.update_invoice_status, name='update_invoice_status'),
  # path('invoice_pdf/<int:id>',views.invoice_pdf,name="invoice_pdf"),
  path('invoice/<int:id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
  path('edit_wallet/<int:id>',views.edit_wallet,name="edit_wallet"),
]
handler404 = 'Billing_App.views.error_page'