from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    employee_type = models.CharField(max_length=50, default='staff', blank=True)
    date_added = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, employee_type='staff')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance, employee_type='staff')

def get_business_profile(self):
    # Owner
    try:
        return self.businessprofile
    except Exception:
        pass
    # Authorized user
    try:
        return self.authorized_businesses.first()
    except Exception:
        return None

User.add_to_class('business_profile', property(get_business_profile))

class BusinessProfile(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('holiday', 'Holiday'),
        ('break', 'Break'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    authorized_users = models.ManyToManyField(User, related_name='authorized_businesses', blank=True)
    business_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    hours = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    logo = models.ImageField(upload_to='business_logos/', null=True, blank=True)
    main_image = models.ImageField(upload_to='business_images/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='closed')
    status_override = models.BooleanField(default=False)
    status_message = models.CharField(max_length=200, blank=True, null=True)
    tags = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.business_name

    def get_current_status(self):
        if self.status_override:
            return self.status
        
        import datetime
        current_time = datetime.datetime.now().time()
        current_day = datetime.datetime.now().strftime('%A').lower()
        
        try:
            hours = self.operating_hours.get(day=current_day)
            if hours.is_closed:
                return 'closed'
            
            opening_time = datetime.datetime.strptime(hours.opening_time, '%H:%M').time()
            closing_time = datetime.datetime.strptime(hours.closing_time, '%H:%M').time()
            
            if opening_time <= current_time <= closing_time:
                return 'open'
            return 'closed'
        except BusinessHours.DoesNotExist:
            return 'closed'

class BusinessHours(models.Model):
    business = models.ForeignKey('BusinessProfile', on_delete=models.CASCADE, related_name='operating_hours')
    day = models.CharField(max_length=10, choices=[
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ])
    opening_time = models.CharField(max_length=5)  # Format: HH:MM
    closing_time = models.CharField(max_length=5)  # Format: HH:MM
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('business', 'day')

    def __str__(self):
        if self.is_closed:
            return f"{self.day.title()}: Closed"
        return f"{self.day.title()}: {self.opening_time} - {self.closing_time}"

class BusinessImage(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='business_images/')
    caption = models.CharField(max_length=200, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.business.business_name}"

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='OrderItem')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.business.business_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
