from django import forms
from django.contrib.auth.models import User
from .models import BusinessProfile, Product, UserProfile
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

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'accept': 'image/*'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        return confirm_password

class BusinessProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    business_email = forms.EmailField(required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = BusinessProfile
        fields = ['business_name']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_business_email(self):
        email = self.cleaned_data.get('business_email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        # Create the user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['business_email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Create the business profile
        business_profile = super().save(commit=False)
        business_profile.user = user
        if commit:
            business_profile.save()
        return business_profile

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
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['image'].required = False

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Product.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError('A product with this name already exists.')
        return name

class AddAuthorizedUserForm(forms.Form):
    email_or_username = forms.CharField(
        label='Email or Username',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter email or username'})
    )
    employee_type = forms.ChoiceField(
        label='Employee Type',
        choices=[
            ('manager', 'Manager'),
            ('employee', 'Employee'),
            ('cashier', 'Cashier'),
        ]
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