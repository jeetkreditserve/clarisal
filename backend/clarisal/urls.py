from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'clarisal-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/', include([
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
        path('org/', include('apps.reports.urls')),
        path('me/', include('apps.employees.self_urls')),
        path('me/', include('apps.documents.self_urls')),
        path('me/', include('apps.approvals.self_urls')),
        path('me/', include('apps.timeoff.self_urls')),
        path('me/', include('apps.attendance.self_urls')),
        path('me/', include('apps.communications.self_urls')),
        path('me/', include('apps.payroll.self_urls')),
        path('me/', include('apps.notifications.urls')),
    ])),
    path('api/v1/', include([
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
        path('org/', include('apps.reports.urls')),
        path('me/', include('apps.employees.self_urls')),
        path('me/', include('apps.documents.self_urls')),
        path('me/', include('apps.approvals.self_urls')),
        path('me/', include('apps.timeoff.self_urls')),
        path('me/', include('apps.attendance.self_urls')),
        path('me/', include('apps.communications.self_urls')),
        path('me/', include('apps.payroll.self_urls')),
        path('me/', include('apps.notifications.urls')),
    ])),
]
