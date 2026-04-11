import os

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'clarisal-api'})


def api_health_check(request):
    return JsonResponse({
        'status': 'ok',
        'version': os.environ.get('GIT_SHA', 'dev'),
    })


def legacy_api_gone(request, legacy_path=''):
    return JsonResponse(
        {'error': f'This API route has moved to /api/{settings.API_VERSION}/.'},
        status=410,
    )


api_v1_patterns = [
    path('health/', api_health_check, name='versioned-health-check'),
    path('auth/', include('apps.accounts.urls')),
    path('ct/', include('apps.organisations.urls')),
    path('ct/', include('apps.invitations.urls')),
    path('ct/', include('apps.audit.urls')),
    path('ct/', include('apps.payroll.ct_urls')),
    path('org/', include('apps.organisations.org_urls')),
    path('org/', include('apps.locations.urls')),
    path('org/', include('apps.departments.urls')),
    path('org/', include('apps.employees.urls')),
    path('org/', include('apps.documents.urls')),
    path('org/', include('apps.approvals.urls')),
    path('org/', include('apps.timeoff.org_urls')),
    path('org/', include('apps.attendance.urls')),
    path('org/', include('apps.communications.urls')),
    path('org/', include('apps.audit.urls')),
    path('org/', include('apps.payroll.org_urls')),
    path('org/', include('apps.expenses.org_urls')),
    path('org/', include('apps.reports.urls')),
    path('org/', include('apps.biometrics.org_urls')),
    path('org/', include('apps.performance.org_urls')),
    path('org/', include('apps.recruitment.urls')),
    path('biometric/', include('apps.biometrics.adms_urls')),
    path('me/', include('apps.employees.self_urls')),
    path('me/', include('apps.documents.self_urls')),
    path('me/', include('apps.approvals.self_urls')),
    path('me/', include('apps.timeoff.self_urls')),
    path('me/', include('apps.attendance.self_urls')),
    path('me/', include('apps.communications.self_urls')),
    path('me/', include('apps.payroll.self_urls')),
    path('me/', include('apps.expenses.self_urls')),
    path('me/', include('apps.notifications.urls')),
    path('me/', include('apps.performance.self_urls')),
    path('org/', include('apps.assets.urls')),
    path('me/', include('apps.assets.self_urls')),
]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/health/', api_health_check, name='health-check'),
    path(f'api/{settings.API_VERSION}/', include(api_v1_patterns)),
    path('api/', legacy_api_gone, name='legacy-api-root-gone'),
    path('api/<path:legacy_path>', legacy_api_gone, name='legacy-api-gone'),
]
