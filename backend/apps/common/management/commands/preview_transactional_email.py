from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandParser

from apps.common.transactional_emails import render_invitation_email, render_password_reset_email


class Command(BaseCommand):
    help = 'Render a transactional email preview without sending mail.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            'kind',
            choices=['invite-org-admin', 'invite-employee', 'password-reset-workforce', 'password-reset-control-tower'],
        )
        parser.add_argument('--base-url', dest='base_url', default=None)

    def handle(self, *args, **options):
        kind = options['kind']
        base_url = options.get('base_url')

        if kind == 'invite-org-admin':
            rendered = render_invitation_email(
                self._build_invite(role='ORG_ADMIN', is_existing_user=False),
                'sample-org-admin-token',
                frontend_url=base_url,
            )
        elif kind == 'invite-employee':
            rendered = render_invitation_email(
                self._build_invite(role='EMPLOYEE', is_existing_user=True),
                'sample-employee-token',
                frontend_url=base_url,
            )
        elif kind == 'password-reset-control-tower':
            rendered = render_password_reset_email(
                self._build_reset_token('CONTROL_TOWER'),
                'sample-control-tower-reset-token',
                frontend_url=base_url,
            )
        else:
            rendered = render_password_reset_email(
                self._build_reset_token('WORKFORCE'),
                'sample-workforce-reset-token',
                frontend_url=base_url,
            )

        self.stdout.write(f'Subject: {rendered.subject}\n')
        self.stdout.write('--- TEXT ---')
        self.stdout.write(rendered.text_body)
        self.stdout.write('\n--- HTML ---')
        self.stdout.write(rendered.html_body)

    @staticmethod
    def _build_invite(*, role: str, is_existing_user: bool):
        class PreviewInvite(SimpleNamespace):
            def get_role_display(self):
                return 'Organisation Admin' if self.role == 'ORG_ADMIN' else 'Employee'

        return PreviewInvite(
            email='info@clarisal.com',
            role=role,
            organisation=SimpleNamespace(name='Orbit Freight Pvt Ltd'),
            invited_by=SimpleNamespace(full_name='Control Tower'),
            user=SimpleNamespace(is_active=is_existing_user, first_name='Jeet'),
            user_id='preview-user-id',
        )

    @staticmethod
    def _build_reset_token(account_type: str):
        return SimpleNamespace(
            user=SimpleNamespace(
                account_type=account_type,
                first_name='Jeet',
                full_name='Jeet',
                email='info@clarisal.com',
            )
        )
