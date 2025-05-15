from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import UserRegistrationForm, BusinessProfileForm, ProductForm
from .models import BusinessProfile, Product, Order
from datetime import datetime

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    products = Product.objects.all()
    return render(request, 'admins/inventory.html', {'products': products})

def landing(request):
    shops = BusinessProfile.objects.all()
    return render(request, 'user/landing.html', {'shops': shops})
    
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = request.user.businessprofile
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('inventory')
    else:
        form = ProductForm()
    return render(request, 'admins/addproduct.html', {'form': form})

def shop_page(request):
    shops = BusinessProfile.objects.all()
    return render(request, 'admins/shop_page.html', {'shops': shops})

def users(request):
    users = User.objects.all()
    return render(request, 'admins/users.html', {'users': users})

def shop_detail_view(request, shop_id):
    try:
        shop = get_object_or_404(BusinessProfile, id=shop_id)
        products = Product.objects.filter(business=shop)
        
        # Get shop status (you can add this logic based on business hours)
        current_time = datetime.now().time()
        shop_status = "OPEN"  # You can add logic to determine if shop is open based on hours
        
        context = {
            'shop': shop,
            'products': products,
            'shop_status': shop_status,
            'current_time': current_time,
        }
        return render(request, 'user/shop.html', context)
    except Exception as e:
        messages.error(request, f'Error loading shop details: {str(e)}')
        return redirect('landing')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if not username or not password1 or not password2:
            messages.error(request, 'All fields are required.')
            return render(request, 'user/register.html')
            
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'user/register.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'user/register.html')
            
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'user/register.html')
            
        try:
            user = User.objects.create_user(username=username, password=password1)
            auth_login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('landing')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, 'user/register.html')
            
    return render(request, 'user/register.html')

@login_required
def create_business_profile(request):
    # Check if user already has a business profile
    try:
        existing_profile = BusinessProfile.objects.get(user=request.user)
        messages.warning(request, 'You already have a business profile.')
        return redirect('shop_page')
    except BusinessProfile.DoesNotExist:
        pass

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, request.FILES)
        if form.is_valid():
            business_profile = form.save(commit=False)
            business_profile.user = request.user
            business_profile.save()
            messages.success(request, 'Business profile created successfully!')
            return redirect('shop_page')
    else:
        form = BusinessProfileForm()
    return render(request, 'user/create_business_profile.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('landing')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'user/login.html')