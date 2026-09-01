from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import AgentProfile, UserRole

User = get_user_model()

class CustomerRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = UserRole.CUSTOMER
        user.is_verified = True
        if commit:
            user.save()
        return user


class AgentRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, label="Agent First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Agent Last Name")
    email = forms.EmailField(required=True, label="Official Email")
    phone_number = forms.CharField(max_length=20, required=True, label="Phone / Mobile")
    
    agency_name = forms.CharField(max_length=150, required=True, label="Agency / Company Name")
    agency_license_no = forms.CharField(max_length=100, required=False, label="IATA / Tourism License No")
    tax_or_pan = forms.CharField(max_length=50, required=True, label="PAN / Tax ID")
    gstin = forms.CharField(max_length=50, required=False, label="GSTIN")
    city = forms.CharField(max_length=100, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = UserRole.AGENT
        if commit:
            user.save()
            AgentProfile.objects.create(
                user=user,
                agency_name=self.cleaned_data['agency_name'],
                agency_license_no=self.cleaned_data.get('agency_license_no', ''),
                tax_or_pan=self.cleaned_data['tax_or_pan'],
                gstin=self.cleaned_data.get('gstin', ''),
                city=self.cleaned_data['city'],
                agency_phone=self.cleaned_data['phone_number'],
                agency_email=self.cleaned_data['email']
            )
        return user
