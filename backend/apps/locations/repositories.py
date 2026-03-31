from .models import OfficeLocation


def list_locations(organisation, include_inactive=False):
    queryset = OfficeLocation.objects.select_related('organisation_address').filter(organisation=organisation).order_by('name')
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def get_location(organisation, pk):
    return OfficeLocation.objects.get(organisation=organisation, id=pk)
