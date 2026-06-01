import json

from django.shortcuts import render
from django.db.models import Sum, F, Count, Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction as db_transaction
from .models import Product, StockTransaction
from .forms import ProductForm, StockTransactionForm, UserRegistrationForm, UserUpdateForm
from .mixins import InventoryPermissionRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User

# ----------------- Dashboard View -----------------
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.all()
        total_products = products.count()
        low_stock = products.filter(quantity_in_stock__lte=F('reorder_level')).count()

        # Total inventory value: SUM(unit_price * quantity_in_stock)
        total_value = products.aggregate(
            val=Sum(F('unit_price') * F('quantity_in_stock'))
        )['val'] or 0

        total_transactions = StockTransaction.objects.count()

        context['stats'] = {
            'total_products': total_products,
            'low_stock_count': low_stock,
            'total_value': total_value,
            'total_transactions': total_transactions,
        }

        # Recent transactions (last 5)
        context['recent_transactions'] = StockTransaction.objects.select_related(
            'product'
        ).order_by('-date')[:5]

        # Chart data: top 10 products by stock quantity
        top_products = products.order_by('-quantity_in_stock')[:10]
        context['stock_chart_data'] = json.dumps({
            'labels': [p.name[:20] for p in top_products],
            'quantities': [p.quantity_in_stock for p in top_products],
            'reorder_levels': [p.reorder_level for p in top_products],
        })

        return context

# ----------------- Product Views -----------------
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category', 'supplier')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q) |
                Q(category__name__icontains=q) |
                Q(supplier__name__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'

class ProductCreateView(InventoryPermissionRequiredMixin, CreateView):
    permission_required = 'inventory.add_product'
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product-list')

    def form_valid(self, form):
        messages.success(self.request, 'Product created successfully.')
        return super().form_valid(form)

class ProductUpdateView(InventoryPermissionRequiredMixin, UpdateView):
    permission_required = 'inventory.change_product'
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product-list')

    def form_valid(self, form):
        messages.success(self.request, 'Product updated.')
        return super().form_valid(form)

class ProductDeleteView(InventoryPermissionRequiredMixin, DeleteView):
    permission_required = 'inventory.delete_product'
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('product-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Product deleted.')
        return super().delete(request, *args, **kwargs)

# ----------------- Stock Transaction Views -----------------
class TransactionListView(LoginRequiredMixin, ListView):
    model = StockTransaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'performed_by')
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(product__name__icontains=q) |
                Q(product__sku__icontains=q) |
                Q(notes__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class TransactionCreateView(InventoryPermissionRequiredMixin, CreateView):
    permission_required = 'inventory.add_stocktransaction'
    model = StockTransaction
    form_class = StockTransactionForm
    template_name = 'inventory/transaction_form.html'
    success_url = reverse_lazy('transaction-list')

    def form_valid(self, form):
        # Perform stock update inside a database transaction
        with db_transaction.atomic():
            transaction = form.save(commit=False)
            transaction.performed_by = self.request.user
            product = transaction.product

            if transaction.transaction_type == StockTransaction.TransactionType.IN:
                product.quantity_in_stock += transaction.quantity
            elif transaction.transaction_type == StockTransaction.TransactionType.OUT:
                if product.quantity_in_stock < transaction.quantity:
                    form.add_error('quantity', 'Insufficient stock.')
                    return self.form_invalid(form)
                product.quantity_in_stock -= transaction.quantity
            elif transaction.transaction_type == StockTransaction.TransactionType.ADJUSTMENT:
                # For an adjustment, we set the stock directly to the entered quantity
                product.quantity_in_stock = transaction.quantity
            else:
                form.add_error('transaction_type', 'Invalid transaction type.')
                return self.form_invalid(form)

            product.save()
            transaction.save()
            messages.success(self.request, 'Transaction recorded and stock updated.')
        return super().form_valid(form)

# ----------------- Registration View -----------------
from django.contrib.auth.views import LoginView
from inventory.forms import CustomAuthenticationForm

class CustomLoginView(LoginView):
    """Login view that uses our custom form for inactive-user messaging."""
    template_name = 'registration/login.html'
    form_class = CustomAuthenticationForm

class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        # Save user with is_active=False — Manager must activate
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        # Assign to Inventory Staff group
        staff_group = Group.objects.get(name='Inventory Staff')
        user.groups.add(staff_group)
        messages.success(
            self.request,
            'Account created! A manager will activate it shortly. You will be able to log in once activated.'
        )
        return super().form_valid(form)


# ----------------- User Management Views -----------------
class UserListView(InventoryPermissionRequiredMixin, ListView):
    """List all users — Inventory Managers only."""
    permission_required = 'auth.view_user'
    model = User
    template_name = 'inventory/user_list.html'
    context_object_name = 'users'
    ordering = ['-date_joined']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(username__icontains=q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class UserEditView(InventoryPermissionRequiredMixin, UpdateView):
    """Edit a user's details, groups, and active status — Inventory Managers only."""
    permission_required = 'auth.change_user'
    model = User
    form_class = UserUpdateForm
    template_name = 'inventory/user_form.html'
    success_url = reverse_lazy('user-list')

    def form_valid(self, form):
        messages.success(self.request, f'User "{form.instance.username}" updated.')
        return super().form_valid(form)


class UserDeleteView(InventoryPermissionRequiredMixin, DeleteView):
    """Delete a user — Inventory Managers only."""
    permission_required = 'auth.delete_user'
    model = User
    template_name = 'inventory/user_confirm_delete.html'
    success_url = reverse_lazy('user-list')

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(request, f'User "{user.username}" deleted.')
        return super().delete(request, *args, **kwargs)
