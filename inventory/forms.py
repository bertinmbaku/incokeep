from django import forms
from .models import Product, StockTransaction
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'supplier', 'unit_price', 'reorder_level']
        # quantity_in_stock is never editable directly – it changes only via StockTransaction

class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['product', 'transaction_type', 'quantity', 'notes']

# ----------------- Registration Form -----------------
class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# ----------------- Custom Login Form -----------------
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, get_user_model

UserModel = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            if self.user_cache is None:
                # Auth failed — check if an inactive user with the correct
                # password exists, so we can show a specific message instead
                # of the generic "invalid username or password".
                try:
                    user = UserModel._default_manager.get_by_natural_key(username)
                    if not user.is_active and user.check_password(password):
                        raise ValidationError(
                            'Your account is pending activation by a manager. '
                            'You will receive access once approved.',
                            code='inactive',
                        )
                except UserModel.DoesNotExist:
                    pass
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

# ----------------- User Management Form -----------------
class UserUpdateForm(forms.ModelForm):
    """Form for managers to edit a user's details, groups, and active status."""
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Roles',
    )
    is_active = forms.BooleanField(
        required=False,
        label='Active',
        help_text='Uncheck to deactivate this account.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'is_active', 'groups']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['username', 'email']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})