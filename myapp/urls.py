from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Existing index route
    path('inventory/', views.inventory, name='inventory'),
    path('user/landing/', views.landing, name='landing'),  # Add this line for the landing page
    path('addproduct/', views.add_product, name='add_product'),
    path('shop_page/', views.shop_page, name='shop_page'),
    path('users/', views.users, name='users'),
    path('shop/<int:shop_id>/', views.shop_detail_view, name='shop_detail'),
]

