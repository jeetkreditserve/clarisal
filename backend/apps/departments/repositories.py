from .models import Department


def list_departments(organisation, include_inactive=False):
    queryset = Department.objects.filter(organisation=organisation).order_by('name')
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def get_department(organisation, pk):
    return Department.objects.get(organisation=organisation, id=pk)
