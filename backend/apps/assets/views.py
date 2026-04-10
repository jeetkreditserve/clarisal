from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from apps.employees.models import Employee

from .models import (
    AssetAssignment,
    AssetCategory,
    AssetIncident,
    AssetItem,
    AssetMaintenance,
    AssetAssignmentStatus,
)
from .serializers import (
    AssetAssignmentSerializer,
    AssetAssignmentWriteSerializer,
    AssetCategorySerializer,
    AssetCategoryWriteSerializer,
    AssetIncidentSerializer,
    AssetIncidentWriteSerializer,
    AssetItemSerializer,
    AssetItemWriteSerializer,
    AssetMaintenanceSerializer,
    AssetMaintenanceWriteSerializer,
    AssetReturnSerializer,
)
from .services import (
    acknowledge_asset_assignment,
    assign_asset_to_employee,
    complete_asset_maintenance,
    create_asset_category,
    create_asset_incident,
    create_asset_item,
    create_asset_maintenance,
    mark_asset_as_lost,
    return_asset,
)


class AssetCategoryListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        categories = AssetCategory.objects.filter(
            organisation=organisation,
            is_active=True
        ).order_by('name')
        return Response(AssetCategorySerializer(categories, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AssetCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = create_asset_category(
            organisation=organisation,
            actor=request.user,
            **serializer.validated_data
        )
        return Response(AssetCategorySerializer(category).data, status=status.HTTP_201_CREATED)


class AssetCategoryDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        category = get_object_or_404(AssetCategory, organisation=organisation, id=pk)
        return Response(AssetCategorySerializer(category).data)

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        category = get_object_or_404(AssetCategory, organisation=organisation, id=pk)
        serializer = AssetCategoryWriteSerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(AssetCategorySerializer(category).data)

    def delete(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        category = get_object_or_404(AssetCategory, organisation=organisation, id=pk)
        category.is_active = False
        category.save(update_fields=['is_active', 'modified_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetItemListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        items = AssetItem.objects.filter(organisation=organisation)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            items = items.filter(lifecycle_status=status_filter)
        
        category_id = request.query_params.get('category')
        if category_id:
            items = items.filter(category_id=category_id)
        
        items = items.order_by('-created_at')
        return Response(AssetItemSerializer(items, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AssetItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = create_asset_item(
            organisation=organisation,
            actor=request.user,
            **serializer.validated_data
        )
        return Response(AssetItemSerializer(item).data, status=status.HTTP_201_CREATED)


class AssetItemDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        item = get_object_or_404(AssetItem, organisation=organisation, id=pk)
        return Response(AssetItemSerializer(item).data)

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        item = get_object_or_404(AssetItem, organisation=organisation, id=pk)
        serializer = AssetItemWriteSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for key, value in serializer.validated_data.items():
            setattr(item, key, value)
        item.save()
        return Response(AssetItemSerializer(item).data)


class AssetAssignmentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        assignments = AssetAssignment.objects.filter(
            asset__organisation=organisation
        ).select_related('asset', 'employee', 'employee__user')
        
        status_filter = request.query_params.get('status')
        if status_filter:
            assignments = assignments.filter(status=status_filter)
        
        employee_id = request.query_params.get('employee')
        if employee_id:
            assignments = assignments.filter(employee_id=employee_id)
        
        assignments = assignments.order_by('-assigned_at')
        return Response(AssetAssignmentSerializer(assignments, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AssetAssignmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        asset = get_object_or_404(
            AssetItem,
            organisation=organisation,
            id=serializer.validated_data['asset_id']
        )
        employee = get_object_or_404(Employee, organisation=organisation, id=request.data.get('employee_id'))
        
        assignment = assign_asset_to_employee(
            asset=asset,
            employee=employee,
            actor=request.user,
            condition_on_issue=serializer.validated_data.get('condition_on_issue'),
            expected_return_date=serializer.validated_data.get('expected_return_date'),
            notes=serializer.validated_data.get('notes', ''),
        )
        return Response(AssetAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class AssetAssignmentDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        assignment = get_object_or_404(
            AssetAssignment,
            asset__organisation=organisation,
            id=pk
        )
        return Response(AssetAssignmentSerializer(assignment).data)


class AssetAssignmentAcknowledgeView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def post(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        assignment = get_object_or_404(
            AssetAssignment,
            asset__organisation=organisation,
            id=pk
        )
        assignment = acknowledge_asset_assignment(assignment, actor=request.user)
        return Response(AssetAssignmentSerializer(assignment).data)


class AssetAssignmentReturnView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def post(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        assignment = get_object_or_404(
            AssetAssignment,
            asset__organisation=organisation,
            id=pk
        )
        serializer = AssetReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = return_asset(
                assignment=assignment,
                condition_on_return=serializer.validated_data.get('condition_on_return'),
                notes=serializer.validated_data.get('notes', ''),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AssetAssignmentSerializer(assignment).data)


class AssetAssignmentLostView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def post(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        assignment = get_object_or_404(
            AssetAssignment,
            asset__organisation=organisation,
            id=pk
        )
        notes = request.data.get('notes', '')
        try:
            assignment = mark_asset_as_lost(assignment, notes=notes, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AssetAssignmentSerializer(assignment).data)


class EmployeeAssetAssignmentsView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        assignments = AssetAssignment.objects.filter(
            employee=employee
        ).select_related('asset')
        return Response(AssetAssignmentSerializer(assignments, many=True).data)


class AssetMaintenanceListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        maintenance = AssetMaintenance.objects.filter(
            asset__organisation=organisation
        ).select_related('asset')
        maintenance = maintenance.order_by('-scheduled_date')
        return Response(AssetMaintenanceSerializer(maintenance, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        asset = get_object_or_404(
            AssetItem,
            organisation=organisation,
            id=request.data.get('asset')
        )
        serializer = AssetMaintenanceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        maintenance = create_asset_maintenance(
            asset=asset,
            actor=request.user,
            **serializer.validated_data
        )
        return Response(AssetMaintenanceSerializer(maintenance).data, status=status.HTTP_201_CREATED)


class AssetMaintenanceDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        maintenance = get_object_or_404(
            AssetMaintenance,
            asset__organisation=organisation,
            id=pk
        )
        if 'completed_date' in request.data:
            notes = request.data.get('notes', '')
            maintenance = complete_asset_maintenance(
                maintenance,
                completed_date=request.data.get('completed_date'),
                notes=notes,
                actor=request.user,
            )
        else:
            serializer = AssetMaintenanceWriteSerializer(maintenance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            for key, value in serializer.validated_data.items():
                setattr(maintenance, key, value)
            maintenance.save()
        return Response(AssetMaintenanceSerializer(maintenance).data)


class AssetIncidentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        incidents = AssetIncident.objects.filter(
            asset__organisation=organisation
        ).select_related('asset', 'employee', 'employee__user')
        incidents = incidents.order_by('-reported_at')
        return Response(AssetIncidentSerializer(incidents, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        asset = get_object_or_404(
            AssetItem,
            organisation=organisation,
            id=request.data.get('asset')
        )
        employee_id = request.data.get('employee')
        employee = None
        if employee_id:
            employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        
        incident = create_asset_incident(
            asset=asset,
            incident_type=request.data.get('incident_type'),
            description=request.data.get('description'),
            employee=employee,
            actor=request.user,
        )
        return Response(AssetIncidentSerializer(incident).data, status=status.HTTP_201_CREATED)


class MyAssetAssignmentsView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        from apps.accounts.workspaces import get_active_employee
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee'}, status=status.HTTP_400_BAD_REQUEST)
        
        assignments = AssetAssignment.objects.filter(
            employee=employee
        ).select_related('asset', 'asset__category')
        return Response(AssetAssignmentSerializer(assignments, many=True).data)


class MyAssetAcknowledgementView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def post(self, request, assignment_id):
        from apps.accounts.workspaces import get_active_employee
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee'}, status=status.HTTP_400_BAD_REQUEST)
        
        assignment = get_object_or_404(
            AssetAssignment,
            id=assignment_id,
            employee=employee,
        )
        try:
            assignment = acknowledge_asset_assignment(assignment, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AssetAssignmentSerializer(assignment).data)
