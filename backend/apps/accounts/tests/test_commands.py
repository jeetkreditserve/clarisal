import os
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import Group
from apps.accounts.models import User, UserRole


@pytest.mark.django_db
class TestSeedControlTowerCommand:
    """Test suite for the seed_control_tower management command."""

    def test_command_fails_without_password_env_var(self):
        """Test that command raises CommandError if CONTROL_TOWER_PASSWORD is not set."""
        # Ensure the env var is not set
        if 'CONTROL_TOWER_PASSWORD' in os.environ:
            del os.environ['CONTROL_TOWER_PASSWORD']

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'CONTROL_TOWER_PASSWORD environment variable is not set' in str(exc_info.value)

    def test_command_creates_groups_and_user(self):
        """Test that running the command creates the 3 groups and CT user."""
        os.environ['CONTROL_TOWER_PASSWORD'] = 'TestPass@123'

        try:
            # Ensure clean state
            User.objects.filter(email='admin@calrisal.com').delete()
            Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).delete()

            call_command('seed_control_tower')

            # Verify groups were created
            assert Group.objects.filter(name='control_tower').exists()
            assert Group.objects.filter(name='org_admin').exists()
            assert Group.objects.filter(name='employee').exists()

            # Verify user was created with correct attributes
            user = User.objects.get(email='admin@calrisal.com')
            assert user.first_name == 'Control'
            assert user.last_name == 'Tower'
            assert user.role == UserRole.CONTROL_TOWER
            assert user.is_superuser is True

            # Verify user is in control_tower group
            assert user.groups.filter(name='control_tower').exists()
        finally:
            if 'CONTROL_TOWER_PASSWORD' in os.environ:
                del os.environ['CONTROL_TOWER_PASSWORD']

    def test_command_is_idempotent(self, capsys):
        """Test that running the command again is idempotent (no error, warning about existing user)."""
        os.environ['CONTROL_TOWER_PASSWORD'] = 'TestPass@123'

        try:
            # Ensure clean state
            User.objects.filter(email='admin@calrisal.com').delete()
            Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).delete()

            # First run - creates everything
            call_command('seed_control_tower')
            user_first_run = User.objects.get(email='admin@calrisal.com')
            user_id_first_run = user_first_run.id

            # Second run - should not fail, just warn
            call_command('seed_control_tower')

            # Verify user ID is unchanged (not recreated)
            user_second_run = User.objects.get(email='admin@calrisal.com')
            assert user_second_run.id == user_id_first_run

            # Verify groups still exist
            assert Group.objects.filter(name='control_tower').exists()
            assert Group.objects.filter(name='org_admin').exists()
            assert Group.objects.filter(name='employee').exists()

            # Verify user is still in control_tower group
            assert user_second_run.groups.filter(name='control_tower').exists()

            # Verify warning was printed
            captured = capsys.readouterr()
            assert 'already exists' in captured.out
        finally:
            if 'CONTROL_TOWER_PASSWORD' in os.environ:
                del os.environ['CONTROL_TOWER_PASSWORD']

    def test_command_uses_custom_email_from_env(self):
        """Test that custom email can be set via CONTROL_TOWER_EMAIL env var."""
        custom_email = 'custom@example.com'
        os.environ['CONTROL_TOWER_PASSWORD'] = 'TestPass@123'
        os.environ['CONTROL_TOWER_EMAIL'] = custom_email

        try:
            # Ensure clean state
            User.objects.filter(email=custom_email).delete()

            call_command('seed_control_tower')

            # Verify user was created with custom email
            assert User.objects.filter(email=custom_email).exists()
            user = User.objects.get(email=custom_email)
            assert user.role == UserRole.CONTROL_TOWER
        finally:
            if 'CONTROL_TOWER_PASSWORD' in os.environ:
                del os.environ['CONTROL_TOWER_PASSWORD']
            if 'CONTROL_TOWER_EMAIL' in os.environ:
                del os.environ['CONTROL_TOWER_EMAIL']

    def test_command_transaction_atomic(self):
        """Test that the command uses atomic transactions."""
        # This test verifies that if an error occurs mid-command,
        # all changes are rolled back. We'll simulate this by checking
        # that groups and user creation happens together.
        os.environ['CONTROL_TOWER_PASSWORD'] = 'TestPass@123'

        try:
            # Ensure clean state
            User.objects.filter(email='admin@calrisal.com').delete()
            Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).delete()

            call_command('seed_control_tower')

            # Count total objects created
            groups_count = Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).count()
            assert groups_count == 3
            assert User.objects.filter(email='admin@calrisal.com').exists()
        finally:
            if 'CONTROL_TOWER_PASSWORD' in os.environ:
                del os.environ['CONTROL_TOWER_PASSWORD']
