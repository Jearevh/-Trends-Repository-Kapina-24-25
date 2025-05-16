"""
URL configuration for kapina project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from myapp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('inventory/', views.inventory, name='inventory'),
    path('add-product/', views.add_product, name='addproduct'),
    path('update-product/<int:product_id>/', views.update_product, name='update_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('shop/', views.shop_page, name='shop_page'),
    path('shop/<int:shop_id>/', views.shop_detail_view, name='shop_detail'),
    path('users/', views.users, name='users'),
    # Authentication URLs
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('register/', views.register, name='register'),
    # Business Profile URLs
    path('create-business-profile/', views.create_business_profile, name='create_business_profile'),
    # Order URLs
    path('create-order/', views.create_order, name='create_order'),
    path('manage-orders/', views.manage_orders, name='manage_orders'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
]

