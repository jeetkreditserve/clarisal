from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'calrisal-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/auth/', include('apps.accounts.urls')),
    # Phase 2+: CT, Org, Employee URLs will be added here
]
