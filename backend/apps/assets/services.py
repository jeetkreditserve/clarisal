from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event

from .models import (
    AssetAssignment,
    AssetAssignmentStatus,
    AssetCategory,
    AssetCondition,
    AssetIncident,
    AssetItem,
    AssetLifecycleStatus,
    AssetMaintenance,
)


def create_asset_category(
    organisation,
    name,
    description='',
    actor=None,
):
    category = AssetCategory.objects.create(
        organisation=organisation,
        name=name,
        description=description,
    )
    log_audit_event(
        actor=actor,
        action='ASSET_CATEGORY_CREATED',
        organisation=organisation,
        target=category,
        payload={'description': f'Created asset category: {name}'},
    )
    return category


def create_asset_item(
    organisation,
    name,
    category=None,
    asset_tag='',
    serial_number='',
    vendor='',
    purchase_date=None,
    purchase_cost=None,
    warranty_expiry=None,
    condition=AssetCondition.NEW,
    notes='',
    metadata=None,
    actor=None,
):
    item = AssetItem.objects.create(
        organisation=organisation,
        category=category,
        name=name,
        asset_tag=asset_tag,
        serial_number=serial_number,
        vendor=vendor,
        purchase_date=purchase_date,
        purchase_cost=purchase_cost,
        warranty_expiry=warranty_expiry,
        condition=condition,
        notes=notes,
        metadata=metadata or {},
    )
    log_audit_event(
        actor=actor,
        action='ASSET_ITEM_CREATED',
        organisation=organisation,
        target=item,
        payload={'description': f'Created asset item: {name}'},
    )
    return item


def assign_asset_to_employee(
    asset,
    employee,
    condition_on_issue=None,
    expected_return_date=None,
    notes='',
    actor=None,
):
    if asset.lifecycle_status != AssetLifecycleStatus.AVAILABLE:
        raise ValueError(f'Asset is not available. Current status: {asset.lifecycle_status}')

    if asset.assignments.filter(status=AssetAssignmentStatus.ACTIVE).exists():
        raise ValueError('Asset is already assigned to an employee')

    with transaction.atomic():
        assignment = AssetAssignment.objects.create(
            asset=asset,
            employee=employee,
            condition_on_issue=condition_on_issue or asset.condition,
            expected_return_date=expected_return_date,
            notes=notes,
        )
        asset.lifecycle_status = AssetLifecycleStatus.ASSIGNED
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_ASSIGNED',
        organisation=asset.organisation,
        target=asset,
        payload={'description': f'Assigned {asset.name} to {employee}', 'assignment_id': str(assignment.id)},
    )
    return assignment


def acknowledge_asset_assignment(assignment, actor=None):
    if assignment.acknowledged_at:
        raise ValueError('Assignment already acknowledged')

    assignment.acknowledged_at = timezone.now()
    assignment.save(update_fields=['acknowledged_at', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_ACKNOWLEDGED',
        organisation=assignment.asset.organisation,
        target=assignment.asset,
        payload={'description': f'{assignment.employee} acknowledged {assignment.asset.name}'},
    )
    return assignment


def return_asset(
    assignment,
    condition_on_return=None,
    notes='',
    actor=None,
):
    if assignment.status != AssetAssignmentStatus.ACTIVE:
        raise ValueError(f'Assignment is not active. Current status: {assignment.status}')

    with transaction.atomic():
        assignment.status = AssetAssignmentStatus.RETURNED
        assignment.returned_at = timezone.now()
        assignment.condition_on_return = condition_on_return
        if notes:
            assignment.notes = f'{assignment.notes}\n{notes}'.strip()
        assignment.save()

        asset = assignment.asset
        asset.lifecycle_status = (
            AssetLifecycleStatus.IN_MAINTENANCE
            if condition_on_return in [AssetCondition.POOR, AssetCondition.DAMAGED]
            else AssetLifecycleStatus.AVAILABLE
        )
        if condition_on_return:
            asset.condition = condition_on_return
        asset.save(update_fields=['lifecycle_status', 'condition', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_RETURNED',
        organisation=assignment.asset.organisation,
        target=assignment.asset,
        payload={
            'description': f'{assignment.employee} returned {assignment.asset.name}',
            'assignment_id': str(assignment.id),
            'condition_on_return': condition_on_return,
        },
    )
    return assignment


def mark_asset_as_lost(assignment, notes='', actor=None):
    if assignment.status != AssetAssignmentStatus.ACTIVE:
        raise ValueError(f'Assignment is not active. Current status: {assignment.status}')

    with transaction.atomic():
        assignment.status = AssetAssignmentStatus.LOST
        assignment.save()

        asset = assignment.asset
        asset.lifecycle_status = AssetLifecycleStatus.LOST
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_LOST',
        organisation=assignment.asset.organisation,
        target=assignment.asset,
        payload={'description': f'{assignment.asset.name} marked as lost', 'assignment_id': str(assignment.id)},
    )
    return assignment


def create_asset_incident(
    asset,
    incident_type,
    description,
    employee=None,
    actor=None,
):
    incident = AssetIncident.objects.create(
        asset=asset,
        employee=employee,
        incident_type=incident_type,
        description=description,
    )

    if incident_type in ['LOSS', 'THEFT']:
        asset.lifecycle_status = AssetLifecycleStatus.LOST
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_INCIDENT_CREATED',
        organisation=asset.organisation,
        target=asset,
        payload={'description': f'Asset incident: {incident_type} for {asset.name}', 'incident_id': str(incident.id)},
    )
    return incident


def schedule_asset_maintenance(
    asset,
    maintenance_type,
    scheduled_date,
    description='',
    cost=None,
    vendor='',
    notes='',
    actor=None,
):
    maintenance = AssetMaintenance.objects.create(
        asset=asset,
        maintenance_type=maintenance_type,
        description=description,
        scheduled_date=scheduled_date,
        cost=cost,
        vendor=vendor,
        notes=notes,
    )

    if asset.lifecycle_status == AssetLifecycleStatus.AVAILABLE:
        asset.lifecycle_status = AssetLifecycleStatus.IN_MAINTENANCE
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_MAINTENANCE_SCHEDULED',
        organisation=asset.organisation,
        target=asset,
        payload={'description': f'Maintenance scheduled for {asset.name}: {maintenance_type}', 'maintenance_id': str(maintenance.id)},
    )
    return maintenance


def complete_asset_maintenance(maintenance, completed_date=None, notes='', actor=None):
    maintenance.completed_date = completed_date or timezone.now().date()
    if notes:
        maintenance.notes = f'{maintenance.notes}\n{notes}'.strip()
    maintenance.save()

    asset = maintenance.asset
    if not asset.maintenance_records.filter(completed_date__isnull=True).exists():
        asset.lifecycle_status = AssetLifecycleStatus.AVAILABLE
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_MAINTENANCE_COMPLETED',
        organisation=asset.organisation,
        target=asset,
        payload={'description': f'Maintenance completed for {asset.name}', 'maintenance_id': str(maintenance.id)},
    )
    return maintenance


def create_asset_maintenance(
    asset,
    maintenance_type,
    description='',
    scheduled_date=None,
    cost=None,
    vendor='',
    notes='',
    actor=None,
):
    maintenance = AssetMaintenance.objects.create(
        asset=asset,
        maintenance_type=maintenance_type,
        description=description,
        scheduled_date=scheduled_date or timezone.now().date(),
        cost=cost,
        vendor=vendor,
        notes=notes,
    )

    if asset.lifecycle_status == AssetLifecycleStatus.AVAILABLE:
        asset.lifecycle_status = AssetLifecycleStatus.IN_MAINTENANCE
        asset.save(update_fields=['lifecycle_status', 'modified_at'])

    log_audit_event(
        actor=actor,
        action='ASSET_MAINTENANCE_CREATED',
        organisation=asset.organisation,
        target=asset,
        payload={'description': f'Maintenance created for {asset.name}: {maintenance_type}', 'maintenance_id': str(maintenance.id)},
    )
    return maintenance


def get_unresolved_asset_assignments(employee):
    from .models import AssetAssignment, AssetAssignmentStatus
    return AssetAssignment.objects.filter(
        employee=employee,
        status=AssetAssignmentStatus.ACTIVE,
    ).select_related('asset', 'asset__category')


def get_employee_asset_summary(employee):
    from .models import AssetAssignment, AssetAssignmentStatus
    assignments = AssetAssignment.objects.filter(employee=employee)
    active_count = assignments.filter(status=AssetAssignmentStatus.ACTIVE).count()
    returned_count = assignments.filter(status=AssetAssignmentStatus.RETURNED).count()
    return {
        'active_assignments': active_count,
        'returned_assignments': returned_count,
        'has_unresolved': active_count > 0,
        'unresolved_assets': [
            {
                'id': str(a.id),
                'asset_id': str(a.asset.id),
                'asset_name': a.asset.name,
                'asset_tag': a.asset.asset_tag,
                'category_name': a.asset.category.name if a.asset.category else None,
                'assigned_at': a.assigned_at.isoformat() if a.assigned_at else None,
                'expected_return_date': a.expected_return_date.isoformat() if a.expected_return_date else None,
            }
            for a in assignments.filter(status=AssetAssignmentStatus.ACTIVE).select_related('asset', 'asset__category')
        ],
    }
