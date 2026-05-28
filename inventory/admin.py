from django.contrib import admin
from .models import Category, Supplier, Product, StockTransaction

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_email']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'quantity_in_stock', 'reorder_level', 'unit_price']
    list_filter = ['category']
    search_fields = ['sku', 'name']

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity', 'date', 'performed_by']
    list_filter = ['transaction_type', 'date']
    readonly_fields = ['date', 'performed_by']  # prevent tampering in admin

from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr']
    list_filter = ['action', 'model_name', 'timestamp']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'timestamp']