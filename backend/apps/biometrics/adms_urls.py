from django.urls import path

from .views import AdmsCdataView, CpPlusExportView, EsslEbioserverEventsView, MantraAebasExportView

urlpatterns = [
    path("adms/iclock/cdata", AdmsCdataView.as_view(), name="biometric-adms-cdata"),
    path(
        "essl/ebioserver/<uuid:device_id>/events/",
        EsslEbioserverEventsView.as_view(),
        name="biometric-essl-ebioserver-events",
    ),
    path("mantra/aebas/<uuid:device_id>/export/", MantraAebasExportView.as_view(), name="biometric-mantra-export"),
    path("cpplus/export/<uuid:device_id>/", CpPlusExportView.as_view(), name="biometric-cpplus-export"),
]
