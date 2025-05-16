from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .forms import UserRegistrationForm, BusinessProfileForm, ProductForm
from .models import BusinessProfile, Product, Order
from datetime import datetime

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.warning(request, 'Please create a business profile first.')
        return redirect('create_business_profile')
        
    # Get products for the user's business only
    products = Product.objects.filter(business=request.user.businessprofile)
    return render(request, 'admins/inventory.html', {'products': products})

def landing(request):
    shops = BusinessProfile.objects.all()
    return render(request, 'user/landing.html', {'shops': shops})
    
def add_product(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.warning(request, 'Please create a business profile first.')
        return redirect('create_business_profile')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = request.user.businessprofile
            product.save()
            return redirect('inventory')
    else:
        form = ProductForm()
    return render(request, 'admins/addproduct.html', {'form': form})

def shop_page(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.warning(request, 'Please create a business profile first.')
        return redirect('create_business_profile')
    
    # Get only the current user's business profile
    shop = request.user.businessprofile
    # Get products for the current shop only
    products = Product.objects.filter(business=shop)
    return render(request, 'admins/shop_page.html', {'shop': shop, 'products': products})

def users(request):
    users = User.objects.all()
    return render(request, 'admins/users.html', {'users': users})

def shop_detail_view(request, shop_id):
    try:
        shop = get_object_or_404(BusinessProfile, id=shop_id)
        # Only get products that belong to this specific shop
        products = Product.objects.filter(business=shop)
        
        # Get shop status (you can add this logic based on business hours)
        current_time = datetime.now().time()
        shop_status = "OPEN"  # You can add logic to determine if shop is open based on hours
        
        return render(request, 'user/shop.html', {
            'shop': shop,
            'products': products,
            'shop_status': shop_status
        })
    except BusinessProfile.DoesNotExist:
        messages.error(request, 'Shop not found.')
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

def is_superuser(user):
    return user.is_superuser

@login_required
@ensure_csrf_cookie
def update_product(request, product_id):
    # Get the product and check if it belongs to the user's business
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has a business profile and if the product belongs to their business
    if not hasattr(request.user, 'businessprofile') or product.business != request.user.businessprofile:
        return JsonResponse({'error': 'You do not have permission to update this product'}, status=403)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'error': form.errors}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
@ensure_csrf_cookie
@require_POST
def delete_product(request, product_id):
    try:
        # Get the product and check if it belongs to the user's business
        product = get_object_or_404(Product, id=product_id)
        
        # Check if user has a business profile and if the product belongs to their business
        if not hasattr(request.user, 'businessprofile') or product.business != request.user.businessprofile:
            return JsonResponse({'error': 'You do not have permission to delete this product'}, status=403)
            
        product.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)