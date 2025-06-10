from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .forms import UserRegistrationForm, BusinessProfileForm, ProductForm, UserProfileForm, AddAuthorizedUserForm, BusinessProfileUpdateForm, BusinessHoursForm, BusinessImageForm
from .models import BusinessProfile, Product, Order, OrderItem, BusinessHours, BusinessImage, UserProfile
from datetime import datetime
from django.db.models import Q
from django.utils import timezone
import os
from django.core.paginator import Paginator
import barcode
from barcode.writer import ImageWriter
import io
import random
import base64
from io import BytesIO
from decimal import Decimal
from django.forms import modelformset_factory

def index(request):
    return render(request, 'admins/base.html')

def inventory(request):
    # Clear any existing messages
    storage = messages.get_messages(request)
    storage.used = True
    
    # Check if user has a business profile
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
        
    # Get products for the user's business only
    products = Product.objects.filter(business=request.user.businessprofile)
    return render(request, 'admins/inventory.html', {'products': products})

def landing(request):
    # Clear any existing messages
    storage = messages.get_messages(request)
    storage.used = True
    
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', '')
    
    if query and search_type:
        if search_type == 'location':
            shops = BusinessProfile.objects.filter(
                Q(business_name__icontains=query) | 
                Q(address__icontains=query)
            )
        elif search_type == 'drink':
            products = Product.objects.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query)
            ).select_related('business')
            shops = BusinessProfile.objects.filter(id__in=products.values_list('business_id', flat=True))
        else:
            shops = BusinessProfile.objects.all()
    else:
        shops = BusinessProfile.objects.all()
    
    paginator = Paginator(shops, 8)  # Show 8 shops per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If it's an AJAX request, return only the new shops
        shops_html = render(request, 'user/shops_partial.html', {'shops': page_obj}).content.decode('utf-8')
        return JsonResponse({
            'shops_html': shops_html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None
        })
    
    return render(request, 'user/landing.html', {
        'shops': page_obj,
        'has_next': page_obj.has_next(),
        'search_query': query,
        'search_type': search_type
    })
    
@login_required
def add_product(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, business=request.user.businessprofile)
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
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ProductForm(business=request.user.businessprofile)
    
    return render(request, 'admins/addproduct.html', {'form': form})

@login_required
def shop_page(request):
    try:
        shop = request.user.businessprofile
        products = Product.objects.filter(business=shop)
        gallery_images = shop.gallery_images.all()
        
        if request.method == 'POST':
            # Handle basic info
            shop.business_name = request.POST.get('business_name')
            shop.address = request.POST.get('address')
            shop.status = request.POST.get('status')
            shop.tags = request.POST.get('tags')
            
            # Parse and save operating hours
            hours_str = request.POST.get('hours', '')  # e.g. "9:00 AM - 5:00 PM"
            if hours_str:
                try:
                    # Parse the hours string
                    opening, closing = hours_str.split('-')
                    opening = opening.strip()
                    closing = closing.strip()
                    
                    # Convert to 24-hour format
                    opening_time = datetime.strptime(opening, '%I:%M %p').strftime('%H:%M')
                    closing_time = datetime.strptime(closing, '%I:%M %p').strftime('%H:%M')
                    
                    # Update or create BusinessHours for each day
                    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    for day in days:
                        BusinessHours.objects.update_or_create(
                            business=shop,
                            day=day,
                            defaults={
                                'opening_time': opening_time,
                                'closing_time': closing_time,
                                'is_closed': False
                            }
                        )
                except Exception as e:
                    print(f"Error saving hours: {str(e)}")
            
            # Handle main image
            if request.FILES.get('main_image'):
                shop.main_image = request.FILES['main_image']
            
            # Handle logo upload
            if request.FILES.get('logo'):
                shop.logo = request.FILES['logo']
            
            shop.save()

            # Handle gallery images
            gallery_images = request.FILES.getlist('gallery_images')
            current_count = shop.gallery_images.count()
            
            if gallery_images and current_count < 4:
                remaining_slots = 4 - current_count
                for image in gallery_images[:remaining_slots]:
                    try:
                        if not image.content_type.startswith('image/'):
                            raise ValueError(f"File {image.name} is not an image")
                        
                        BusinessImage.objects.create(
                            business=shop,
                            image=image
                        )
                    except Exception as e:
                        return JsonResponse({
                            'error': f'Error saving gallery image {image.name}: {str(e)}'
                        }, status=400)

            # Return updated data for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Get the current day's hours
                current_day = datetime.now().strftime('%A').lower()
                current_hours = shop.operating_hours.filter(day=current_day).first()
                hours_display = "Hours not specified"
                
                if current_hours:
                    opening = datetime.strptime(current_hours.opening_time, '%H:%M').strftime('%I:%M %p')
                    closing = datetime.strptime(current_hours.closing_time, '%H:%M').strftime('%I:%M %p')
                    hours_display = f"{opening} - {closing}"
                
                return JsonResponse({
                    'success': True,
                    'message': 'Shop details updated successfully',
                    'data': {
                        'business_name': shop.business_name,
                        'address': shop.address,
                        'hours': hours_display,
                        'tags': shop.tags,
                        'status': shop.status,
                        'main_image_url': shop.main_image.url if shop.main_image else None,
                        'logo_url': shop.logo.url if shop.logo else None,
                    }
                })
            else:
                messages.success(request, 'Shop details updated successfully!')
                return redirect('shop_page')
        
        # Get current hours for display
        current_day = datetime.now().strftime('%A').lower()
        current_hours = shop.operating_hours.filter(day=current_day).first()
        hours_display = "8:00 AM - 11:00 PM"  # Default hours
        
        if current_hours:
            opening = datetime.strptime(current_hours.opening_time, '%H:%M').strftime('%I:%M %p')
            closing = datetime.strptime(current_hours.closing_time, '%H:%M').strftime('%I:%M %p')
            hours_display = f"{opening} - {closing}"
        
        context = {
            'business': shop,
            'products': products,
            'gallery_images': gallery_images,
            'hours': hours_display,
        }
        return render(request, 'admins/shop_page.html', context)
    except BusinessProfile.DoesNotExist:
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({
            'error': f'Error updating shop details: {str(e)}'
        }, status=500)

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
                
                # Check if user is already authorized
                if user in authorized_users:
                    messages.error(request, 'User is already authorized.')
                else:
                    # Add user to authorized users
                    request.user.businessprofile.authorized_users.add(user)
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
        
        # Get shop status from the model
        shop_status = shop.get_status_display()
        
        context = {
            'shop': shop,
            'products': products,
            'shop_status': shop_status,
        }
        return render(request, 'user/shop.html', context)
    except Exception as e:
        messages.error(request, f'Error loading shop details: {str(e)}')
        return redirect('landing')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Registration successful!')
                return redirect('landing')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
    else:
        form = UserRegistrationForm()
            
    return render(request, 'user/register.html', {'form': form})

@login_required
def create_business_profile(request):
    if request.method == 'POST':
        try:
            # Create or update business profile
            business_profile = BusinessProfile.objects.create(
                user=request.user,
                business_name=request.POST.get('business_name'),
                address=request.POST.get('address'),
                hours=request.POST.get('operating_hours'),  # Use the simple hours field
            )
            
            messages.success(request, 'Business profile created successfully!')
            return redirect('shop_page')
            
        except Exception as e:
            messages.error(request, f'Error creating business profile: {str(e)}')
            return redirect('create_business_profile')
            
    return render(request, 'user/create_business_profile.html')

def custom_login(request):
    # Clear any existing messages
    storage = messages.get_messages(request)
    storage.used = True  # Mark all messages as used
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Create UserProfile if it doesn't exist
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'employee_type': 'staff'}
            )
            
            # Get the next URL if it exists
            next_url = request.GET.get('next', 'landing')
            return redirect(next_url)
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
        # Check if the new name already exists for this business
        new_name = request.POST.get('name')
        if new_name:
            existing_product = Product.objects.filter(
                name__iexact=new_name,
                business=request.user.businessprofile
            ).exclude(id=product_id).first()
            
            if existing_product:
                return JsonResponse({
                    'error': f'A product with the name "{new_name}" already exists in your business.'
                }, status=400)
        
        form = ProductForm(request.POST, request.FILES, instance=product, business=request.user.businessprofile)
        if form.is_valid():
            try:
                # If a new image is uploaded, delete the old one
                if 'image' in request.FILES and product.image:
                    try:
                        # Delete the old image file if it exists
                        if os.path.isfile(product.image.path):
                            os.remove(product.image.path)
                    except Exception as e:
                        print(f"Error deleting old image: {e}")
                
                updated_product = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Product updated successfully',
                    'product': {
                        'name': updated_product.name,
                        'description': updated_product.description,
                        'price': str(updated_product.price),
                        'image_url': updated_product.image.url if updated_product.image else None
                    }
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list[0]
            return JsonResponse({'error': errors}, status=400)
    
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
        'address': shop.address,
        'hours': shop.hours or 'Hours not specified',
        'logo_url': shop.logo.url if shop.logo else None
    } for shop in shops]
    
    return JsonResponse(results, safe=False)

def search_drink(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)
    
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query)
    ).select_related('business')[:10]  # Limit to 10 results
    
    results = [{
        'id': product.id,
        'name': product.name,
        'description': product.description or 'No description available',
        'price': str(product.price),
        'image_url': product.image.url if product.image else None,
        'business_name': product.business.business_name,
        'business_id': product.business.id
    } for product in products]
    
    return JsonResponse(results, safe=False)

def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('landing')
    return redirect('landing')

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

@login_required
@require_POST
def remove_authorized_user(request):
    if not request.user.businessprofile or request.user != request.user.businessprofile.user:
        return JsonResponse({'error': 'Only the business owner can remove authorized users'}, status=403)
    
    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'User ID is required'}, status=400)
        
    try:
        user = User.objects.get(id=user_id)
        # Don't allow removing the owner
        if user == request.user.businessprofile.user:
            return JsonResponse({'error': 'Cannot remove the business owner'}, status=400)
            
        request.user.businessprofile.authorized_users.remove(user)
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def manage_shop(request):
    if not hasattr(request.user, 'businessprofile'):
        messages.error(request, 'You need to create a business profile first.')
        return redirect('create_business_profile')

    business = request.user.businessprofile

    if request.method == 'POST':
        form = BusinessProfileUpdateForm(request.POST, request.FILES, instance=business)
        
        try:
            if form.is_valid():
                # Save the main form
                business_profile = form.save()
                
                # Update hours if provided
                if 'hours' in request.POST:
                    business_profile.hours = request.POST['hours']
                    business_profile.save()

                # Handle gallery images
                gallery_images = request.FILES.getlist('gallery_images')
                if gallery_images:
                    for image in gallery_images:
                        try:
                            print(f"Processing image: {image.name}, size: {image.size}")
                            # Validate image
                            if not image.content_type.startswith('image/'):
                                raise ValueError(f"File {image.name} is not an image")
                            
                            # Create the gallery image
                            new_image = BusinessImage.objects.create(
                                business=business,
                                image=image
                            )
                            print(f"Created new image: {new_image.id}, path: {new_image.image.path}")
                        except Exception as e:
                            print(f"Error saving image {image.name}: {str(e)}")
                            return JsonResponse({
                                'error': f'Error saving gallery image {image.name}: {str(e)}'
                            }, status=400)

                messages.success(request, 'Shop details updated successfully.')
                return JsonResponse({
                    'success': True,
                    'message': 'Shop details updated successfully'
                })
            else:
                print("Form validation errors:", form.errors)
                return JsonResponse({'error': form.errors}, status=400)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({
                'error': f'Error updating shop details: {str(e)}'
            }, status=500)

    else:
        form = BusinessProfileUpdateForm(instance=business)

    context = {
        'form': form,
        'business': business
    }
    return render(request, 'admins/shop_page.html', context)

@login_required
@require_POST
def remove_gallery_image(request, image_id):
    try:
        image = BusinessImage.objects.get(id=image_id)
        if image.business.user != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            
        # Delete the actual image file
        if image.image:
            image.image.delete()
        
        # Delete the database record
        image.delete()
        return JsonResponse({'success': True})
    except BusinessImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def test_view(request):
    return render(request, 'admins/test.html')

@login_required
@require_POST
def remove_main_image(request):
    try:
        business = request.user.businessprofile
        if business.main_image:
            business.main_image.delete()  # This will delete the file
            business.main_image = None    # This will clear the field
            business.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def remove_logo(request):
    try:
        business = request.user.businessprofile
        if business.logo:
            business.logo.delete()  # This will delete the file
            business.logo = None    # This will clear the field
            business.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
