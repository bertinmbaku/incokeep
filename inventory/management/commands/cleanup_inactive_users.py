"""
Management command to delete user accounts that were registered
but never activated by a manager within a configurable number of days.

Usage:
    python manage.py cleanup_inactive_users          # default: 30 days
    python manage.py cleanup_inactive_users --days 7  # custom threshold
    python manage.py cleanup_inactive_users --dry-run  # show what would be deleted
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Delete inactive user accounts older than a specified number of days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete accounts inactive for longer than this many days (default: 30).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which accounts would be deleted without actually deleting them.',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)

        stale_users = User.objects.filter(
            is_active=False,
            date_joined__lt=cutoff,
        )

        count = stale_users.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                f'No inactive accounts older than {days} days found.'
            ))
            return

        self.stdout.write(
            f'Found {count} inactive account(s) older than {days} days:'
        )

        for user in stale_users:
            self.stdout.write(
                f'  - {user.username} (registered {user.date_joined.date()}, '
                f'never activated)'
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] — {count} account(s) would be deleted. '
                    f'Run without --dry-run to execute.'
                )
            )
        else:
            stale_users.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCleaned up {count} stale account(s).'
                )
            )
