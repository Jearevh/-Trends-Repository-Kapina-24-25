from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .forms import UserRegistrationForm, BusinessProfileForm, ProductForm, UserProfileForm
from .models import BusinessProfile, Product, Order, OrderItem
from datetime import datetime
from django.db.models import Q
from django.contrib.auth import logout
from django.shortcuts import redirect
import barcode
from barcode.writer import ImageWriter
import io
import random
import base64
from io import BytesIO
from decimal import Decimal

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    # Check if user has a business profile
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
        
    # Get products for the user's business only
    products = Product.objects.filter(business=request.user.businessprofile)
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
        # Only get products that belong to this specific shop
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

@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            return redirect('landing')
    else:
        form = UserProfileForm(instance=request.user.userprofile)
    return render(request, 'user/update_profile.html', {'form': form})

@login_required
def update_user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.user != user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to update this profile.')
        return redirect('landing')
        
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('landing')
    else:
        form = UserProfileForm(instance=user.userprofile)
    return render(request, 'user/update_profile.html', {'form': form})

def search_location(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)
    
    shops = BusinessProfile.objects.filter(
        Q(business_name__icontains=query) | 
        Q(address__icontains=query)
    )[:10]  # Limit to 10 results
    
    results = [{
        'id': shop.id,
        'name': shop.business_name,
        'address': shop.address
    } for shop in shops]
    
    return JsonResponse(results, safe=False)

def search_drink(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query)
    )[:10]  # Limit to 10 results
    
    results = [{
        'id': product.id,
        'name': product.name,
        'description': product.description or ''
    } for product in products]
    
    return JsonResponse(results, safe=False)

def custom_logout(request):
    logout(request)
    return redirect('landing')  # Redirect to a landing page or any other page after logout

# Function to generate a random barcode
@login_required
def generate_random_barcode(request):
    # Generate a random number for the barcode
    random_number = str(random.randint(100000000000, 999999999999))
    # Generate the barcode
    ean = barcode.get('ean13', random_number, writer=ImageWriter())
    buffer = io.BytesIO()
    ean.write(buffer)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='image/png')

@login_required
def get_order_details(request):
    # Example logic to fetch order details
    order_details = {
        'items': [
            {'name': 'Spanish Latte', 'price': 49},
            {'name': 'Caramel Macchiato', 'price': 49},
        ],
        'total': 98
    }
    return JsonResponse(order_details)

@login_required
def create_order(request, shop_id):
    if request.method == 'POST':
        try:
            business = get_object_or_404(BusinessProfile, id=shop_id)
            order_items = request.POST.getlist('items')
            
            # Calculate total amount
            total_amount = Decimal('0.00')
            items_data = []
            
            for item_data in order_items:
                product_id = item_data.get('product_id')
                quantity = int(item_data.get('quantity', 1))
                product = get_object_or_404(Product, id=product_id)
                price = product.price * quantity
                total_amount += price
                items_data.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price
                })
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                business=business,
                total_amount=total_amount,
                status='pending'
            )
            
            # Create order items
            for item_data in items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'redirect_url': reverse('order_overview', args=[order.id])
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def order_overview(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Generate barcode
    barcode_class = barcode.get_barcode_class('code128')
    barcode_instance = barcode_class(str(order.id), writer=ImageWriter())
    buffer = BytesIO()
    barcode_instance.write(buffer)
    barcode_image = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'order': order,
        'barcode': barcode_image,
    }
    
    return render(request, 'user/order_overview.html', context)