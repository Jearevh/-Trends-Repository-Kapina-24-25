from django.shortcuts import render

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    return render(request, 'admins/inventory.html')

def landing(request):
    return render(request, 'user/landing.html')
    
def add_product(request):
    return render(request, 'admins/addproduct.html')

def shop_page(request):
    return render(request, 'admins/shop_page.html')

def users(request):
    return render(request, 'admins/users.html')