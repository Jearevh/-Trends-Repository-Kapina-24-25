from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('inventory/', views.admin_inventory_view, name='inventory'),
]
