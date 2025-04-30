from django.shortcuts import render

def landing_page(request):
    return render(request, 'user/landing.html')

def admin_inventory_view(request):
    return render(request, 'admins/inventory.html')