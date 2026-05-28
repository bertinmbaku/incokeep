import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .current_user import get_current_user

# Temporary storage to hold the pre-save state of an instance.
# Key = instance id, Value = dict of field values
_pre_save_states = {}

@receiver(pre_save, sender='inventory.Product')
def capture_pre_save_state(sender, instance, **kwargs):
    """
    Before a Product is saved, store a copy of its current database values.
    If it's a new object (pk is None), we store an empty dict.
    """
    from .models import Product  # Import here to avoid circular imports
    if instance.pk is None:
        # This is a new object; no previous state.
        _pre_save_states[id(instance)] = {}
    else:
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            # Build a dict of field names to their old values.
            old_state = {
                field.name: getattr(old_instance, field.name)
                for field in Product._meta.fields
                if field.name not in ('created_at', 'updated_at')  # ignore auto timestamps
            }
            _pre_save_states[id(instance)] = old_state
        except Product.DoesNotExist:
            _pre_save_states[id(instance)] = {}

@receiver(post_save, sender='inventory.Product')
def log_product_save_with_diff(sender, instance, created, **kwargs):
    """
    After the Product is saved, retrieve the pre-save state and compute the diff.
    """
    from .models import Product, AuditLog  # Import here to avoid circular imports
    user = get_current_user()
    instance_id = id(instance)
    old_state = _pre_save_states.pop(instance_id, {})

    if created:
        action = 'CREATE'
        changes = json.dumps({'new': _serializable_fields(instance)})
    else:
        action = 'UPDATE'
        # Compare old_state with the current instance
        new_state = {
            field.name: getattr(instance, field.name)
            for field in Product._meta.fields
            if field.name not in ('created_at', 'updated_at')
        }
        changes_dict = {}
        for field_name in new_state:
            old_val = old_state.get(field_name)
            new_val = new_state[field_name]
            # Convert values to a serializable format (e.g., datetime -> str)
            old_val_serial = _serialize_value(old_val)
            new_val_serial = _serialize_value(new_val)
            if old_val_serial != new_val_serial:
                changes_dict[field_name] = {
                    'old': old_val_serial,
                    'new': new_val_serial,
                }
        changes = json.dumps(changes_dict) if changes_dict else '{}'

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name='Product',
        object_id=instance.pk,
        object_repr=str(instance),
        changes=changes,
    )

@receiver(post_delete, sender='inventory.Product')
def log_product_delete(sender, instance, **kwargs):
    """
    Log the full state of the product at the moment of deletion.
    """
    user = get_current_user()
    full_state = _serializable_fields(instance)
    from .models import AuditLog  # Import here to avoid circular imports
    AuditLog.objects.create(
        user=user,
        action='DELETE',
        model_name='Product',
        object_id=instance.pk,
        object_repr=str(instance),
        changes=json.dumps({'deleted': full_state}),
    )

def _serializable_fields(instance):
    """Return a dict of the instance's fields suitable for JSON serialization."""
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        data[field.name] = _serialize_value(value)
    return data

def _serialize_value(value):
    from django.db.models import Model
    from django.utils import timezone
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(value, Model):
        return str(value)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, timezone.datetime):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)   # or str(value) if you prefer exactness
    else:
        return value