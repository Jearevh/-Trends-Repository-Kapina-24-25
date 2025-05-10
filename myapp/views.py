from django.shortcuts import render

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    return render(request, 'admins/inventory.html')

def landing(request):
    return render(request, 'user/landing.html')