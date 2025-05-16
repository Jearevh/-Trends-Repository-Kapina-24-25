from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .forms import UserRegistrationForm, BusinessProfileForm, ProductForm, UserProfileForm, AddAuthorizedUserForm
from .models import BusinessProfile, Product, Order
from datetime import datetime
from django.db.models import Q
from django.utils import timezone
import os

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
    
@login_required
def add_product(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.business = request.user.businessprofile
                product.save()
                messages.success(request, 'Product added successfully!')
                return redirect('inventory')
            except Exception as e:
                messages.error(request, f'Error adding product: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    return render(request, 'admins/addproduct.html', {'form': form})

def shop_page(request):
    shops = BusinessProfile.objects.all()
    return render(request, 'admins/shop_page.html', {'shops': shops})

@login_required
def users(request):
    # Check if user has a business profile
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
    
    # Get only the authorized users for this business
    authorized_users = request.user.businessprofile.authorized_users.all()
    
    # Add the owner to the list if they're not already in it
    if request.user not in authorized_users:
        authorized_users = list(authorized_users)
        authorized_users.insert(0, request.user)
    
    if request.method == 'POST' and 'add_authorized_user' in request.POST:
        # Only business owner can add users
        if request.user == request.user.businessprofile.user:
            form = AddAuthorizedUserForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['email_or_username']
                employee_type = form.cleaned_data['employee_type']
                
                # Check if user is already authorized
                if user in authorized_users:
                    messages.error(request, 'User is already authorized.')
                else:
                    # Add user to authorized users
                    request.user.businessprofile.authorized_users.add(user)
                    # Set employee type
                    user.employee_type = employee_type
                    user.save()
                    messages.success(request, f'Successfully authorized {user.username}.')
                    return redirect('users')
        else:
            messages.error(request, 'Only the business owner can add authorized users.')
    else:
        form = AddAuthorizedUserForm()
    
    context = {
        'users': authorized_users,
        'business': request.user.businessprofile,
        'add_user_form': form,
        'is_owner': request.user == request.user.businessprofile.user
    }
    return render(request, 'admins/users.html', context)

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
            # Create UserProfile if it doesn't exist
            if not hasattr(user, 'userprofile'):
                from .models import UserProfile
                UserProfile.objects.create(user=user)
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
            try:
                # If a new image is uploaded, delete the old one
                if 'image' in request.FILES and product.image:
                    # Delete the old image file
                    if os.path.isfile(product.image.path):
                        os.remove(product.image.path)
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Product updated successfully',
                    'product': {
                        'name': product.name,
                        'description': product.description,
                        'price': str(product.price),
                        'image_url': product.image.url if product.image else None
                    }
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
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
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully'
            })
        return JsonResponse({
            'success': False,
            'error': 'Invalid form data'
        })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

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
    auth_logout(request)
    return redirect('landing')