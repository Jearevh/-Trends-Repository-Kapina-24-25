from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import BusinessProfile, Product, UserProfile, BusinessHours, BusinessImage
from django.db import models

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'accept': 'image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.save()
            profile.save()
        return profile

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
        error_messages = {
            'username': {
                'unique': 'A user with that username already exists.',
            }
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help text and customize error messages
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        # Make all fields required
        for field in self.fields.values():
            field.error_messages = {'required': 'This field is required.'}
    
    def _post_clean(self):
        super()._post_clean()
        # Remove password validation errors
        if 'password2' in self._errors:
            password2_errors = self._errors['password2']
            # Keep only the password mismatch error if it exists
            mismatch_error = "The two password fields didn't match."
            if mismatch_error in password2_errors:
                self._errors['password2'] = [mismatch_error]
            else:
                del self._errors['password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create UserProfile for the new user
            UserProfile.objects.create(user=user)
        return user

class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = ['business_name', 'address', 'hours', 'first_name', 'last_name']
        
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    operating_hours = forms.CharField(
        max_length=100,
        required=True,
        initial='9:00 AM - 5:00 PM',
        help_text='Enter your business hours (e.g., 9:00 AM - 5:00 PM)'
    )

    def save(self, user=None, commit=True):
        profile = super().save(commit=False)
        if user:
            profile.user = user
        if commit:
            profile.save()
            # Update user's name
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()
        return profile

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'})
        }

    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['image'].required = False

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not self.business:
            return name
            
        # Check if a product with this name exists in the same business
        query = Product.objects.filter(
            name__iexact=name,
            business=self.business
        )
        
        # If this is an update (instance exists), exclude the current instance
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise forms.ValidationError('A product with this name already exists in your business.')
            
        return name

class AddAuthorizedUserForm(forms.Form):
    email_or_username = forms.CharField(
        label='Email or Username',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter email or username'})
    )

    def clean_email_or_username(self):
        data = self.cleaned_data['email_or_username']
        try:
            # Try to find user by username or email
            user = User.objects.get(
                models.Q(username=data) | models.Q(email=data)
            )
            return user
        except User.DoesNotExist:
            raise forms.ValidationError('User not found. Please check the email or username.') 

class BusinessHoursForm(forms.ModelForm):
    class Meta:
        model = BusinessHours
        fields = ['day', 'opening_time', 'closing_time', 'is_closed']
        widgets = {
            'day': forms.HiddenInput(),
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'closed-checkbox'})
        }

class BusinessImageForm(forms.ModelForm):
    class Meta:
        model = BusinessImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }

class BusinessProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = ['business_name', 'address', 'hours', 'description', 'main_image', 'status', 'status_message']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'status': forms.Select(choices=BusinessProfile.STATUS_CHOICES),
            'hours': forms.TextInput(attrs={
                'placeholder': 'e.g., 9:00 AM - 5:00 PM',
                'class': 'shop-hours'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget.attrs['class'] = 'status-select'
        self.fields['status_message'].widget.attrs['class'] = 'status-message-input' 