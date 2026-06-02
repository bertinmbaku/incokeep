"""
Management command to populate the database with demo data:
products, categories, suppliers, staff users, managers, and transactions.

Usage:
    python manage.py populate_demo_data
    python manage.py populate_demo_data --reset   # wipe existing data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from inventory.models import Category, Supplier, Product, StockTransaction


DEMO_CATEGORIES = [
    {'name': 'Electronics', 'description': 'Electronic devices and accessories'},
    {'name': 'Furniture', 'description': 'Office and home furniture'},
    {'name': 'Stationery', 'description': 'Paper, pens, and office supplies'},
    {'name': 'Cleaning', 'description': 'Cleaning supplies and equipment'},
    {'name': 'IT Equipment', 'description': 'Computers, networking, and peripherals'},
]

DEMO_SUPPLIERS = [
    {'name': 'TechSource Ltd', 'contact_email': 'sales@techsource.example.com', 'phone': '555-0101'},
    {'name': 'OfficeMax Supplies', 'contact_email': 'orders@officemax.example.com', 'phone': '555-0102'},
    {'name': 'CleanPro Distributors', 'contact_email': 'info@cleanpro.example.com', 'phone': '555-0103'},
    {'name': 'FurniWorld Inc', 'contact_email': 'support@furniworld.example.com', 'phone': '555-0104'},
    {'name': 'Global Stationery Co', 'contact_email': 'sales@globalstationery.example.com', 'phone': '555-0105'},
]

DEMO_PRODUCTS = [
    # Electronics
    {'sku': 'ELC-001', 'name': 'Wireless Mouse', 'category': 'Electronics', 'supplier': 'TechSource Ltd', 'unit_price': 24.99, 'quantity': 45, 'reorder': 10},
    {'sku': 'ELC-002', 'name': 'USB-C Hub 7-in-1', 'category': 'Electronics', 'supplier': 'TechSource Ltd', 'unit_price': 49.99, 'quantity': 30, 'reorder': 8},
    {'sku': 'ELC-003', 'name': 'Bluetooth Speaker', 'category': 'Electronics', 'supplier': 'TechSource Ltd', 'unit_price': 79.99, 'quantity': 5, 'reorder': 10},
    {'sku': 'ELC-004', 'name': 'HDMI Cable 2m', 'category': 'Electronics', 'supplier': 'TechSource Ltd', 'unit_price': 12.99, 'quantity': 100, 'reorder': 20},
    {'sku': 'ELC-005', 'name': 'Noise-Cancelling Headphones', 'category': 'Electronics', 'supplier': 'TechSource Ltd', 'unit_price': 149.99, 'quantity': 3, 'reorder': 5},
    # Furniture
    {'sku': 'FUR-001', 'name': 'Ergonomic Office Chair', 'category': 'Furniture', 'supplier': 'FurniWorld Inc', 'unit_price': 299.99, 'quantity': 12, 'reorder': 5},
    {'sku': 'FUR-002', 'name': 'Standing Desk 120cm', 'category': 'Furniture', 'supplier': 'FurniWorld Inc', 'unit_price': 449.99, 'quantity': 4, 'reorder': 3},
    {'sku': 'FUR-003', 'name': 'Filing Cabinet 3-Drawer', 'category': 'Furniture', 'supplier': 'FurniWorld Inc', 'unit_price': 189.99, 'quantity': 8, 'reorder': 4},
    {'sku': 'FUR-004', 'name': 'Monitor Stand Riser', 'category': 'Furniture', 'supplier': 'FurniWorld Inc', 'unit_price': 34.99, 'quantity': 25, 'reorder': 10},
    # Stationery
    {'sku': 'STA-001', 'name': 'A4 Printer Paper (500 sheets)', 'category': 'Stationery', 'supplier': 'Global Stationery Co', 'unit_price': 5.99, 'quantity': 200, 'reorder': 50},
    {'sku': 'STA-002', 'name': 'Ballpoint Pen Box (50pk)', 'category': 'Stationery', 'supplier': 'Global Stationery Co', 'unit_price': 8.99, 'quantity': 60, 'reorder': 20},
    {'sku': 'STA-003', 'name': 'Sticky Notes (12 pads)', 'category': 'Stationery', 'supplier': 'Global Stationery Co', 'unit_price': 6.49, 'quantity': 40, 'reorder': 15},
    {'sku': 'STA-004', 'name': 'Permanent Markers (4pk)', 'category': 'Stationery', 'supplier': 'Global Stationery Co', 'unit_price': 3.99, 'quantity': 2, 'reorder': 10},
    # Cleaning
    {'sku': 'CLN-001', 'name': 'All-Purpose Cleaner 5L', 'category': 'Cleaning', 'supplier': 'CleanPro Distributors', 'unit_price': 12.99, 'quantity': 15, 'reorder': 5},
    {'sku': 'CLN-002', 'name': 'Microfiber Cloths (20pk)', 'category': 'Cleaning', 'supplier': 'CleanPro Distributors', 'unit_price': 9.99, 'quantity': 0, 'reorder': 10},
    {'sku': 'CLN-003', 'name': 'Hand Sanitizer 1L', 'category': 'Cleaning', 'supplier': 'CleanPro Distributors', 'unit_price': 7.49, 'quantity': 22, 'reorder': 10},
    # IT Equipment
    {'sku': 'ITE-001', 'name': 'Laptop 15" i5/16GB/512GB', 'category': 'IT Equipment', 'supplier': 'TechSource Ltd', 'unit_price': 899.99, 'quantity': 6, 'reorder': 3},
    {'sku': 'ITE-002', 'name': '24" IPS Monitor', 'category': 'IT Equipment', 'supplier': 'TechSource Ltd', 'unit_price': 199.99, 'quantity': 10, 'reorder': 5},
    {'sku': 'ITE-003', 'name': 'Mechanical Keyboard', 'category': 'IT Equipment', 'supplier': 'TechSource Ltd', 'unit_price': 89.99, 'quantity': 18, 'reorder': 8},
    {'sku': 'ITE-004', 'name': 'Network Switch 8-Port', 'category': 'IT Equipment', 'supplier': 'TechSource Ltd', 'unit_price': 45.99, 'quantity': 7, 'reorder': 4},
]

DEMO_USERS = [
    {'username': 'manager1', 'email': 'manager1@incokeep.example.com', 'password': 'Manager123!', 'group': 'Inventory Managers', 'first_name': 'Alice', 'last_name': 'Chen'},
    {'username': 'manager2', 'email': 'manager2@incokeep.example.com', 'password': 'Manager123!', 'group': 'Inventory Managers', 'first_name': 'Bob', 'last_name': 'Patel'},
    {'username': 'staff1', 'email': 'staff1@incokeep.example.com', 'password': 'Staff123!', 'group': 'Inventory Staff', 'first_name': 'Carol', 'last_name': 'Diaz'},
    {'username': 'staff2', 'email': 'staff2@incokeep.example.com', 'password': 'Staff123!', 'group': 'Inventory Staff', 'first_name': 'David', 'last_name': 'Kim'},
    {'username': 'staff3', 'email': 'staff3@incokeep.example.com', 'password': 'Staff123!', 'group': 'Inventory Staff', 'first_name': 'Eva', 'last_name': 'Müller'},
    {'username': 'staff4', 'email': 'staff4@incokeep.example.com', 'password': 'Staff123!', 'group': 'Inventory Staff', 'first_name': 'Frank', 'last_name': 'Okafor'},
]


class Command(BaseCommand):
    help = 'Populate the database with demo products, categories, suppliers, and users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing inventory data before populating.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting all inventory data...'))
            StockTransaction.objects.all().delete()
            Product.objects.all().delete()
            Supplier.objects.all().delete()
            Category.objects.all().delete()

        # ---------- Categories ----------
        categories = {}
        for cat_data in DEMO_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']},
            )
            categories[cat_data['name']] = obj
            if created:
                self.stdout.write(f'  + Category: {obj.name}')
            else:
                self.stdout.write(f'  = Category: {obj.name} (already exists)')

        # ---------- Suppliers ----------
        suppliers = {}
        for sup_data in DEMO_SUPPLIERS:
            obj, created = Supplier.objects.get_or_create(
                name=sup_data['name'],
                defaults={
                    'contact_email': sup_data['contact_email'],
                    'phone': sup_data['phone'],
                },
            )
            suppliers[sup_data['name']] = obj
            if created:
                self.stdout.write(f'  + Supplier: {obj.name}')
            else:
                self.stdout.write(f'  = Supplier: {obj.name} (already exists)')

        # ---------- Products ----------
        for prod_data in DEMO_PRODUCTS:
            obj, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'category': categories[prod_data['category']],
                    'supplier': suppliers[prod_data['supplier']],
                    'unit_price': prod_data['unit_price'],
                    'quantity_in_stock': prod_data['quantity'],
                    'reorder_level': prod_data['reorder'],
                },
            )
            if created:
                self.stdout.write(f'  + Product: {obj.name} ({obj.sku})')
            else:
                self.stdout.write(f'  = Product: {obj.name} ({obj.sku}) (already exists)')

        # ---------- Users ----------
        for user_data in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': True,
                },
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
            group = Group.objects.get(name=user_data['group'])
            user.groups.add(group)
            if created:
                self.stdout.write(f'  + User: {user.username} ({user_data["group"]})')
            else:
                self.stdout.write(f'  = User: {user.username} ({user_data["group"]}) (already exists)')

        # ---------- Sample Transactions ----------
        if not StockTransaction.objects.exists():
            products = list(Product.objects.all())
            manager = User.objects.filter(groups__name='Inventory Managers').first()
            staff = User.objects.filter(groups__name='Inventory Staff').first()
            user = manager or staff

            if products and user:
                tx_data = [
                    (products[0], 'IN', 20, 'Initial stock import'),
                    (products[1], 'IN', 15, 'Supplier delivery #A-101'),
                    (products[2], 'IN', 10, 'Supplier delivery #A-102'),
                    (products[5], 'OUT', 2, 'Issued to Marketing dept'),
                    (products[8], 'OUT', 50, 'Monthly stationery distribution'),
                    (products[0], 'OUT', 3, 'Replacement for faulty unit'),
                    (products[15], 'IN', 5, 'New hardware rollout'),
                    (products[6], 'OUT', 1, 'Transferred to Branch B'),
                ]
                for product, ttype, qty, note in tx_data:
                    # Adjust stock for OUT transactions so we don't go negative
                    if ttype == 'OUT' and product.quantity_in_stock < qty:
                        product.quantity_in_stock += qty  # top up first
                        product.save()
                    StockTransaction.objects.create(
                        product=product,
                        transaction_type=ttype,
                        quantity=qty,
                        performed_by=user,
                        notes=note,
                    )
                    if ttype == 'IN':
                        product.quantity_in_stock += qty
                    elif ttype == 'OUT':
                        product.quantity_in_stock -= qty
                    product.save()
                self.stdout.write(self.style.SUCCESS(f'  + Created {len(tx_data)} sample transactions'))

        self.stdout.write(self.style.SUCCESS('\n✓ Demo data population complete.'))
        self.stdout.write(f'  Products:  {Product.objects.count()}')
        self.stdout.write(f'  Suppliers: {Supplier.objects.count()}')
        self.stdout.write(f'  Categories:{Category.objects.count()}')
        self.stdout.write(f'  Users:     {User.objects.count()}')
        self.stdout.write(f'  TX Logs:   {StockTransaction.objects.count()}')
        self.stdout.write('\n  Login credentials:')
        self.stdout.write('    Manager: manager1 / Manager123!')
        self.stdout.write('    Staff:   staff1   / Staff123!')
