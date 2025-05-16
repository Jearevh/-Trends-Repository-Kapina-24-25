from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('inventory/', views.inventory, name='inventory'),
    path('shop/', views.shop_page, name='shop_page'),
    path('users/', views.users, name='users'),
    path('shop/<int:shop_id>/', views.shop_detail_view, name='shop_detail'),
    path('register/', views.register, name='register'),
    path('create_business_profile/', views.create_business_profile, name='create_business_profile'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('addproduct/', views.add_product, name='addproduct'),
    path('update_product/<int:product_id>/', views.update_product, name='update_product'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('update_profile_picture/', views.update_profile_picture, name='update_profile_picture'),
    path('update_user_profile/<int:user_id>/', views.update_user_profile, name='update_user_profile'),
    path('search/location/', views.search_location, name='search_location'),
    path('search/drink/', views.search_drink, name='search_drink'),
    path('generate-barcode/', views.generate_random_barcode, name='generate_barcode'),
    path('get-order-details/', views.get_order_details, name='get_order_details'),
    path('shop/<int:shop_id>/create-order/', views.create_order, name='create_order'),
    path('order/<int:order_id>/', views.order_overview, name='order_overview'),
]

