from django.urls import path

from .views import AdmsCdataView, EsslEbioserverEventsView

urlpatterns = [
    path('adms/iclock/cdata', AdmsCdataView.as_view(), name='biometric-adms-cdata'),
    path('essl/ebioserver/<uuid:device_id>/events/', EsslEbioserverEventsView.as_view(), name='biometric-essl-ebioserver-events'),
]
