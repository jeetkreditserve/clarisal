from unittest.mock import patch

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.notifications.tasks import send_approval_outcome_email, send_payroll_ready_email


@pytest.mark.django_db
def test_send_approval_outcome_email_uses_transactional_email_renderer():
    user = User.objects.create_user(
        email='approval-email@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
        first_name='Approval',
    )

    with patch('apps.notifications.tasks.send_transactional_email') as mock_send:
        send_approval_outcome_email(
            str(user.id),
            subject='Your leave request has been approved',
            title='Approval complete',
            body='Your leave request has been approved.',
        )

    mock_send.assert_called_once()


@pytest.mark.django_db
def test_send_payroll_ready_email_uses_payslip_path():
    user = User.objects.create_user(
        email='payroll-email@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
        first_name='Payroll',
    )

    with patch('apps.notifications.tasks.send_transactional_email') as mock_send:
        send_payroll_ready_email(str(user.id), pay_period='April 2026')

    mock_send.assert_called_once()
