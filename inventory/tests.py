from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .models import Category, Supplier, Product, StockTransaction, AuditLog
from inventory.current_user import set_current_user

# -------------------------------------------------------------------
# Model tests
# -------------------------------------------------------------------
class ProductModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            sku='SKU001',
            name='Test Item',
            unit_price=9.99,
            quantity_in_stock=20,
            reorder_level=10
        )

    def test_low_stock_false(self):
        self.assertFalse(self.product.is_low_stock)

    def test_low_stock_true(self):
        self.product.quantity_in_stock = 5
        self.assertTrue(self.product.is_low_stock)

    def test_string_representation(self):
        self.assertEqual(str(self.product), 'Test Item (SKU001)')


class StockTransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass123')
        self.product = Product.objects.create(
            sku='SKU100', name='Widget', unit_price=5.00, quantity_in_stock=100
        )

    def test_transaction_str(self):
        tx = StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            quantity=10,
            performed_by=self.user
        )
        self.assertIn('Stock In', str(tx))


# -------------------------------------------------------------------
# Business logic tests (stock adjustments)
# -------------------------------------------------------------------
class StockTransactionLogicTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('staff', password='testpass123')
        staff_group, _ = Group.objects.get_or_create(name='Inventory Staff')
        self.user.groups.add(staff_group)
        self.product = Product.objects.create(
            sku='SKU200', name='Gadget', unit_price=10.00, quantity_in_stock=50
        )
        self.client.login(username='staff', password='testpass123')

    def test_stock_in_increases_quantity(self):
        self.client.post(reverse('transaction-create'), {
            'product': self.product.pk,
            'transaction_type': 'IN',
            'quantity': 20,
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 70)

    def test_stock_out_decreases_quantity(self):
        self.client.post(reverse('transaction-create'), {
            'product': self.product.pk,
            'transaction_type': 'OUT',
            'quantity': 10,
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 40)

    def test_stock_out_insufficient_returns_error(self):
        response = self.client.post(reverse('transaction-create'), {
            'product': self.product.pk,
            'transaction_type': 'OUT',
            'quantity': 999,
        })
        self.assertEqual(response.status_code, 200)        # form re‑displayed
        self.assertContains(response, 'Insufficient stock')
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 50)   # unchanged

    def test_adjustment_sets_exact_quantity(self):
        self.client.post(reverse('transaction-create'), {
            'product': self.product.pk,
            'transaction_type': 'ADJ',
            'quantity': 30,
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 30)


# -------------------------------------------------------------------
# Permission tests
# -------------------------------------------------------------------
class PermissionTest(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.manager.groups.add(manager_group)

        self.staff = User.objects.create_user('staff2', password='testpass123')
        staff_group = Group.objects.get(name='Inventory Staff')
        self.staff.groups.add(staff_group)

        self.product = Product.objects.create(
            sku='SKU300', name='Secret Gadget', unit_price=99.99
        )

    def test_staff_cannot_edit_product(self):
        self.client.login(username='staff2', password='testpass123')
        response = self.client.get(reverse('product-edit', args=[self.product.pk]))
        self.assertEqual(response.status_code, 404)   # our mixin returns 404

    def test_manager_can_edit_product(self):
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('product-edit', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('product-list'))
        self.assertRedirects(response, '/accounts/login/?next=/products/')

    def test_anonymous_cannot_create_transaction(self):
        response = self.client.get(reverse('transaction-create'))
        self.assertRedirects(response, '/accounts/login/?next=/transactions/new/')


# -------------------------------------------------------------------
# View tests
# -------------------------------------------------------------------
class ProductViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('viewer', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.user.groups.add(manager_group)
        self.client.login(username='viewer', password='testpass123')
        self.product = Product.objects.create(sku='VW001', name='Viewable', unit_price=1.00)

    def test_product_list_view(self):
        response = self.client.get(reverse('product-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Viewable')

    def test_product_detail_view(self):
        # self.product is already created in setUp with unit_price
        response = self.client.get(reverse('product-detail', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_product_create_view(self):
        response = self.client.get(reverse('product-create'))
        self.assertEqual(response.status_code, 200)

    def test_product_create_post(self):
        response = self.client.post(reverse('product-create'), {
            'sku': 'NEW001',
            'name': 'New Product',
            'unit_price': 5.00,
            'reorder_level': 5,
        })
        self.assertRedirects(response, reverse('product-list'))
        self.assertTrue(Product.objects.filter(sku='NEW001').exists())


class TransactionViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('txuser', password='testpass123')
        staff_group = Group.objects.get(name='Inventory Staff')
        self.user.groups.add(staff_group)
        self.client.login(username='txuser', password='testpass123')
        self.product = Product.objects.create(sku='TX001', name='Tx Product', unit_price=1.00)

    def test_transaction_list_view(self):
        response = self.client.get(reverse('transaction-list'))
        self.assertEqual(response.status_code, 200)

    def test_transaction_create_view(self):
        response = self.client.get(reverse('transaction-create'))
        self.assertEqual(response.status_code, 200)


# -------------------------------------------------------------------
# Audit log tests
# -------------------------------------------------------------------
class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('auditor', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.user.groups.add(manager_group)
        self.client.login(username='auditor', password='testpass123')
        set_current_user(self.user)          # manually set for signal

    def tearDown(self):
        set_current_user(None)               # clear after test
        super().tearDown()

    def test_create_logs_audit_entry(self):
        product = Product.objects.create(sku='AUD001', name='Audit Product', unit_price=1.00)
        log = AuditLog.objects.filter(
            model_name='Product',
            object_id=product.pk,
            action='CREATE'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)

    def test_update_logs_audit_entry(self):
        product = Product.objects.create(sku='AUD002', name='Before Edit', unit_price=2.00)
        product.name = 'After Edit'
        product.save()
        log = AuditLog.objects.filter(
            model_name='Product',
            object_id=product.pk,
            action='UPDATE'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)

    def test_delete_logs_audit_entry(self):
        product = Product.objects.create(sku='AUD003', name='To Delete', unit_price=3.00)
        product_id = product.pk
        product.delete()
        log = AuditLog.objects.filter(
            model_name='Product',
            object_id=product_id,
            action='DELETE'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)

# -------------------------------------------------------------------
# Security tests (axes, CSRF, admin URL)
# -------------------------------------------------------------------
class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        # We need a user for brute-force testing
        User.objects.create_user('victim', password='correct123')

    def test_admin_hidden(self):
        response = self.client.get('/admin/')
        # With a custom ADMIN_URL, the default should 404
        self.assertEqual(response.status_code, 404)

    def test_csrf_cookie_set(self):
        response = self.client.get(reverse('login'))
        self.assertIn('csrftoken', response.cookies)

    def test_brute_force_lockout(self):
        for _ in range(5):
            self.client.post(reverse('login'), {
                'username': 'victim',
                'password': 'wrong',
            })
        response = self.client.post(reverse('login'), {
            'username': 'victim',
            'password': 'stillwrong',
        })
        self.assertEqual(response.status_code, 429)

# -------------------------------------------------------------------
# Registration tests
# -------------------------------------------------------------------
class RegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')

    def test_register_creates_inactive_user(self):
        response = self.client.post(reverse('register'), {
            'username': 'newhire',
            'email': 'newhire@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='newhire')
        self.assertFalse(user.is_active)                          # Manager must activate

    def test_register_adds_to_staff_group(self):
        self.client.post(reverse('register'), {
            'username': 'worker',
            'email': 'worker@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        user = User.objects.get(username='worker')
        self.assertTrue(user.groups.filter(name='Inventory Staff').exists())

    def test_inactive_user_cannot_login(self):
        # Register
        self.client.post(reverse('register'), {
            'username': 'pending',
            'email': 'pending@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        # Try to log in with correct credentials
        logged_in = self.client.login(username='pending', password='ComplexPass123!')
        self.assertFalse(logged_in)                                # Blocked until activated

    def test_inactive_user_gets_activation_message(self):
        # Register — account goes to is_active=False
        self.client.post(reverse('register'), {
            'username': 'awaiting',
            'email': 'awaiting@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        # Try logging in with correct password
        response = self.client.post(reverse('login'), {
            'username': 'awaiting',
            'password': 'ComplexPass123!',
        })
        self.assertEqual(response.status_code, 200)                # Stays on login page
        self.assertContains(response, 'pending activation by a manager')


# -------------------------------------------------------------------
# Cleanup command tests
# -------------------------------------------------------------------
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

class CleanupCommandTest(TestCase):
    def setUp(self):
        self.active = User.objects.create_user('active_user', password='testpass123')
        # Inactive user, recently registered — should survive
        self.recent = User.objects.create_user(
            'recent_user', password='testpass123', is_active=False,
            date_joined=timezone.now(),
        )
        # Inactive user, 60 days old — should be cleaned up
        self.stale = User.objects.create_user(
            'stale_user', password='testpass123', is_active=False,
            date_joined=timezone.now() - timedelta(days=60),
        )

    def test_cleanup_deletes_stale_users(self):
        call_command('cleanup_inactive_users', days=30, stdout=None)
        self.assertTrue(User.objects.filter(username='active_user').exists())
        self.assertTrue(User.objects.filter(username='recent_user').exists())
        self.assertFalse(User.objects.filter(username='stale_user').exists())

    def test_cleanup_dry_run_does_not_delete(self):
        call_command('cleanup_inactive_users', days=30, dry_run=True, stdout=None)
        # All three should still exist
        self.assertTrue(User.objects.filter(username='active_user').exists())
        self.assertTrue(User.objects.filter(username='recent_user').exists())
        self.assertTrue(User.objects.filter(username='stale_user').exists())


# -------------------------------------------------------------------
# Search tests
# -------------------------------------------------------------------
class ProductSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('searcher', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.user.groups.add(manager_group)
        self.client.login(username='searcher', password='testpass123')

        self.cat_electronics = Category.objects.create(name='Electronics')
        self.cat_furniture = Category.objects.create(name='Furniture')
        self.supplier_abc = Supplier.objects.create(name='ABC Supplies')
        self.supplier_xyz = Supplier.objects.create(name='XYZ Corp')

        Product.objects.create(
            sku='LAP-001', name='Laptop Pro', category=self.cat_electronics,
            supplier=self.supplier_abc, unit_price=999.99, quantity_in_stock=10
        )
        Product.objects.create(
            sku='DSK-001', name='Desk Chair', category=self.cat_furniture,
            supplier=self.supplier_xyz, unit_price=149.99, quantity_in_stock=25
        )
        Product.objects.create(
            sku='MON-001', name='Monitor 4K', category=self.cat_electronics,
            supplier=self.supplier_abc, unit_price=399.99, quantity_in_stock=8
        )

    def test_search_by_name_exact(self):
        response = self.client.get(reverse('product-list'), {'q': 'Laptop Pro'})
        self.assertContains(response, 'Laptop Pro')
        self.assertNotContains(response, 'Desk Chair')
        self.assertNotContains(response, 'Monitor 4K')

    def test_search_by_name_partial(self):
        response = self.client.get(reverse('product-list'), {'q': 'Desk'})
        self.assertContains(response, 'Desk Chair')
        self.assertNotContains(response, 'Laptop Pro')

    def test_search_case_insensitive(self):
        response = self.client.get(reverse('product-list'), {'q': 'laptop pro'})
        self.assertContains(response, 'Laptop Pro')

        response = self.client.get(reverse('product-list'), {'q': 'MONITOR'})
        self.assertContains(response, 'Monitor 4K')

    def test_search_by_sku(self):
        response = self.client.get(reverse('product-list'), {'q': 'DSK-001'})
        self.assertContains(response, 'Desk Chair')
        self.assertNotContains(response, 'Laptop Pro')

    def test_search_by_sku_partial(self):
        response = self.client.get(reverse('product-list'), {'q': 'LAP'})
        self.assertContains(response, 'Laptop Pro')
        self.assertNotContains(response, 'Desk Chair')

    def test_search_by_category(self):
        response = self.client.get(reverse('product-list'), {'q': 'Furniture'})
        self.assertContains(response, 'Desk Chair')
        self.assertNotContains(response, 'Laptop Pro')

    def test_search_by_supplier(self):
        response = self.client.get(reverse('product-list'), {'q': 'XYZ'})
        self.assertContains(response, 'Desk Chair')
        self.assertNotContains(response, 'Laptop Pro')

    def test_search_no_match(self):
        response = self.client.get(reverse('product-list'), {'q': 'zzznotfound'})
        self.assertContains(response, 'No products yet.')

    def test_empty_search_returns_all(self):
        response = self.client.get(reverse('product-list'), {'q': ''})
        self.assertContains(response, 'Laptop Pro')
        self.assertContains(response, 'Desk Chair')
        self.assertContains(response, 'Monitor 4K')

    def test_search_preserves_query_in_input(self):
        response = self.client.get(reverse('product-list'), {'q': 'Laptop'})
        self.assertContains(response, 'value="Laptop"')


class TransactionSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('txsearcher', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.user.groups.add(manager_group)
        self.client.login(username='txsearcher', password='testpass123')

        self.product_a = Product.objects.create(
            sku='SKU-A', name='Alpha Widget', unit_price=10.00
        )
        self.product_b = Product.objects.create(
            sku='SKU-B', name='Beta Gadget', unit_price=20.00
        )
        StockTransaction.objects.create(
            product=self.product_a, transaction_type='IN',
            quantity=5, performed_by=self.user, notes='Restock from supplier'
        )
        StockTransaction.objects.create(
            product=self.product_b, transaction_type='OUT',
            quantity=2, performed_by=self.user, notes='Customer order #1234'
        )

    def test_search_by_product_name(self):
        response = self.client.get(reverse('transaction-list'), {'q': 'Alpha'})
        self.assertContains(response, 'Alpha Widget')
        self.assertNotContains(response, 'Beta Gadget')

    def test_search_by_product_sku(self):
        response = self.client.get(reverse('transaction-list'), {'q': 'SKU-B'})
        self.assertContains(response, 'Beta Gadget')
        self.assertNotContains(response, 'Alpha Widget')

    def test_search_by_notes(self):
        response = self.client.get(reverse('transaction-list'), {'q': 'Restock'})
        self.assertContains(response, 'Restock from supplier')
        self.assertNotContains(response, 'Customer order')

    def test_search_transactions_case_insensitive(self):
        response = self.client.get(reverse('transaction-list'), {'q': 'alpha widget'})
        self.assertContains(response, 'Alpha Widget')


class UserSearchTest(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('mgmt', password='testpass123')
        manager_group = Group.objects.get(name='Inventory Managers')
        self.manager.groups.add(manager_group)
        self.client.login(username='mgmt', password='testpass123')

        User.objects.create_user('alice_wonder', email='alice@example.com')
        User.objects.create_user('bob_builder', email='bob@example.com')
        User.objects.create_user('charlie_dev', email='charlie@example.com')

    def test_search_by_username(self):
        response = self.client.get(reverse('user-list'), {'q': 'alice'})
        self.assertContains(response, 'alice_wonder')
        self.assertNotContains(response, 'bob_builder')
        self.assertNotContains(response, 'charlie_dev')

    def test_search_by_username_case_insensitive(self):
        response = self.client.get(reverse('user-list'), {'q': 'ALICE'})
        self.assertContains(response, 'alice_wonder')

    def test_search_does_not_match_email(self):
        response = self.client.get(reverse('user-list'), {'q': 'alice@example.com'})
        self.assertNotContains(response, 'alice_wonder')
        self.assertContains(response, 'No users found.')

    def test_search_no_match(self):
        response = self.client.get(reverse('user-list'), {'q': 'nonexistent'})
        self.assertContains(response, 'No users found.')