from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_groups(sender, **kwargs):
    """Create default groups and assign permissions after migrations."""
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    # Fetch content types
    product_ct = ContentType.objects.get_for_model(sender.get_model('Product'))
    transaction_ct = ContentType.objects.get_for_model(sender.get_model('StockTransaction'))
    category_ct = ContentType.objects.get_for_model(sender.get_model('Category'))
    supplier_ct = ContentType.objects.get_for_model(sender.get_model('Supplier'))
    audit_ct = ContentType.objects.get_for_model(sender.get_model('AuditLog'))

    # ---- Individual permissions ----
    # Products
    view_product = Permission.objects.get(codename='view_product', content_type=product_ct)
    add_product = Permission.objects.get(codename='add_product', content_type=product_ct)
    change_product = Permission.objects.get(codename='change_product', content_type=product_ct)
    delete_product = Permission.objects.get(codename='delete_product', content_type=product_ct)
    # Transactions
    view_transaction = Permission.objects.get(codename='view_stocktransaction', content_type=transaction_ct)
    add_transaction = Permission.objects.get(codename='add_stocktransaction', content_type=transaction_ct)
    # Categories
    view_category = Permission.objects.get(codename='view_category', content_type=category_ct)
    add_category = Permission.objects.get(codename='add_category', content_type=category_ct)
    change_category = Permission.objects.get(codename='change_category', content_type=category_ct)
    # Suppliers
    view_supplier = Permission.objects.get(codename='view_supplier', content_type=supplier_ct)
    add_supplier = Permission.objects.get(codename='add_supplier', content_type=supplier_ct)
    change_supplier = Permission.objects.get(codename='change_supplier', content_type=supplier_ct)
    # Audit
    view_audit = Permission.objects.get(codename='view_auditlog', content_type=audit_ct)

    # Auth (User management) — User model lives in the 'auth' app
    user_ct = ContentType.objects.get(app_label='auth', model='user')
    view_user = Permission.objects.get(codename='view_user', content_type=user_ct)
    change_user = Permission.objects.get(codename='change_user', content_type=user_ct)
    delete_user = Permission.objects.get(codename='delete_user', content_type=user_ct)

    # ---- Inventory Managers ----
    manager_group, _ = Group.objects.get_or_create(name='Inventory Managers')
    manager_group.permissions.set([
        view_product, add_product, change_product, delete_product,
        view_transaction, add_transaction,
        view_category, add_category, change_category,
        view_supplier, add_supplier, change_supplier,
        view_audit,
        view_user, change_user, delete_user,
    ])

    # ---- Inventory Staff ----
    staff_group, _ = Group.objects.get_or_create(name='Inventory Staff')
    staff_group.permissions.set([
        view_product,
        view_transaction, add_transaction,
        view_category,
        view_supplier,
    ])


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        # Import signals for audit trail
        import inventory.signals  # noqa
        # Connect group creation AFTER all migrations
        post_migrate.connect(create_groups, sender=self)