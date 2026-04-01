from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccountType, EmailAddress, PasswordResetToken, Person, PhoneNumber, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('email', 'account_type')
    list_display = (
        'email',
        'person',
        'account_type',
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
    )
    list_filter = ('account_type', 'role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'modified_at', 'last_login')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'person', 'account_type', 'role', 'organisation')}),
        ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Metadata', {'fields': ('is_onboarding_email_sent', 'last_login', 'created_at', 'modified_at')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'account_type',
                    'password1',
                    'password2',
                    'role',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organisation', 'person')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'modified_at')
    search_fields = ('id', 'email_addresses__email', 'phone_numbers__e164_number')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('email', 'person', 'kind', 'is_primary', 'is_login', 'is_verified')
    list_filter = ('kind', 'is_primary', 'is_login', 'is_verified')
    search_fields = ('email', 'normalized_email')
    readonly_fields = ('normalized_email', 'created_at', 'modified_at')


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('e164_number', 'person', 'kind', 'is_primary', 'is_verified')
    list_filter = ('kind', 'is_primary', 'is_verified')
    search_fields = ('e164_number', 'display_number')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at', 'created_at')
    list_filter = ('used_at', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('token_hash', 'requested_by_ip', 'created_at')
