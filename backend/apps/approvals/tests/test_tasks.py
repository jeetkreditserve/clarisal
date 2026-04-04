from unittest.mock import patch

import pytest

from apps.approvals.tasks import process_pending_action_escalations_task, send_pending_action_reminders_task


@pytest.mark.django_db
class TestApprovalTasks:
    def test_send_pending_action_reminders_task_respects_lock(self):
        with (
            patch('apps.approvals.tasks.cache.add', return_value=True),
            patch('apps.approvals.tasks.cache.delete'),
            patch('apps.approvals.tasks.send_pending_action_reminders', return_value=2) as mock_runner,
        ):
            changed = send_pending_action_reminders_task()

        assert changed == 2
        mock_runner.assert_called_once()

    def test_process_pending_action_escalations_task_skips_without_lock(self):
        with (
            patch('apps.approvals.tasks.cache.add', return_value=False),
            patch('apps.approvals.tasks.process_pending_action_escalations') as mock_runner,
        ):
            changed = process_pending_action_escalations_task()

        assert changed == 0
        mock_runner.assert_not_called()
