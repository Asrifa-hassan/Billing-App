from django.urls import path
from . import views

urlpatterns = [
    # Home & Auth
    path('', views.index, name='index'),
    path('login_page/', views.login_page, name='login_page'),
    path('logout_page/', views.logout_page, name='logout_page'),
    path('register/', views.register, name='register'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Staff Management
    path('staff/', views.staff, name='staff'),
    path('activate_staff/<int:id>/', views.activate_staff, name='activate_staff'),
    path('add_staff/', views.add_staff, name='add_staff'),
    path('update_staff/<int:id>/', views.update_staff, name='update_staff'),
    path('delete_staff/<int:id>/', views.delete_staff, name='delete_staff'),
    path('view_staff/<int:id>/', views.view_staff, name='view_staff'),

    # Products
    path('products/', views.products_list, name='products_list'),
    path('view/<int:id>/', views.product_view, name='product_view'),
    path('add_product/', views.add_product, name='add_product'),
    path('update_product/<int:id>/', views.update_product, name='update_product'),
    path('del_product/<int:id>/', views.del_product, name='del_product'),
    path("search_product/", views.search_product, name="search_product"),
    path('set_customer/', views.set_customer, name='set_customer'),


    # Customers
    path('customers/', views.customers, name='customers'),
    path('new_customer/', views.new_customer, name='new_customer'),
    path('edit_customer/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path("search_customer/", views.search_customer, name="search_customer"),
    # path('set_customer_ajax/<int:customer_id>/', views.set_customer_ajax, name='set_customer_ajax'),
    path('edit_wallet/<int:id>/', views.edit_wallet, name='edit_wallet'),


    path("add_to_cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("update_cart_item/", views.update_cart_item, name="update_cart_item"),

    # Invoices
    path('update_quantity/', views.update_quantity, name='update_quantity'),
    path('invoices/', views.invoices, name='invoices'),
    path("create_invoice/", views.create_invoice, name="create_invoice"),
    path('invoice/<int:id>/view/', views.invoice_view, name='invoice_view'),
    path('edit_invoice/<int:invoice_id>/', views.edit_invoice, name='edit_invoice'),
    path('invoice/<int:id>/delete/', views.delete_invoice, name='delete_invoice'),
    path('update_invoice_status/<int:id>/', views.update_invoice_status, name='update_invoice_status'),
    path('invoice/<int:id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoice/<int:id>/make_payment/', views.make_payment, name='make_payment'),
    path("assign-customer-to-cart/", views.assign_customer_to_cart, name="assign_customer_to_cart"),
    path('update_payment/<int:cart_id>/', views.update_payment, name='update_payment'),
    path("clear_invoice/", views.clear_invoice, name="clear_invoice"),
    path('save_invoice/', views.save_invoice, name='save_invoice'),
    path("record_payment/<int:cart_id>/", views.record_payment, name="record_payment"),


]


# Custom 404 handler
handler404 = 'Billing_App.views.error_page'
