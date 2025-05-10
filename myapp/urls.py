from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Existing index route
    path('inventory/', views.inventory, name='inventory'),
    path('user/landing/', views.landing, name='landing'),  # Add this line for the landing page
]

