from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'clarisal-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/ct/', include('apps.organisations.urls')),
    path('api/ct/', include('apps.invitations.urls')),
    path('api/ct/', include('apps.audit.urls')),
    path('api/ct/', include('apps.payroll.ct_urls')),
    path('api/org/', include('apps.organisations.org_urls')),
    path('api/org/', include('apps.locations.urls')),
    path('api/org/', include('apps.departments.urls')),
    path('api/org/', include('apps.employees.urls')),
    path('api/org/', include('apps.documents.urls')),
    path('api/org/', include('apps.approvals.urls')),
    path('api/org/', include('apps.timeoff.org_urls')),
    path('api/org/', include('apps.communications.urls')),
    path('api/org/', include('apps.audit.urls')),
    path('api/org/', include('apps.payroll.org_urls')),
    path('api/me/', include('apps.employees.self_urls')),
    path('api/me/', include('apps.documents.self_urls')),
    path('api/me/', include('apps.approvals.self_urls')),
    path('api/me/', include('apps.timeoff.self_urls')),
    path('api/me/', include('apps.communications.self_urls')),
    path('api/me/', include('apps.payroll.self_urls')),
]
