from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.employees.models import Employee

from .models import Document, EmployeeDocumentRequest
from .repositories import list_documents
from .serializers import (
    DocumentSerializer,
    EmployeeDocumentRequestSerializer,
    LegacyUploadDocumentSerializer,
    OnboardingDocumentTypeSerializer,
    RejectDocumentSerializer,
    UploadRequestedDocumentSerializer,
)
from .services import (
    assign_document_requests,
    generate_download_url,
    list_document_requests,
    list_onboarding_document_types,
    reject_document,
    upload_document,
    upload_document_request,
    verify_document,
)


class DocumentTypeListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        return Response(OnboardingDocumentTypeSerializer(list_onboarding_document_types(), many=True).data)


class EmployeeDocumentRequestListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        return Response(EmployeeDocumentRequestSerializer(list_document_requests(employee), many=True).data)

    def post(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        document_type_ids = request.data.get('document_type_ids') or []
        try:
            requests = assign_document_requests(employee, document_type_ids, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmployeeDocumentRequestSerializer(requests, many=True).data, status=status.HTTP_201_CREATED)


class EmployeeDocumentListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        return Response(DocumentSerializer(list_documents(employee), many=True).data)


class EmployeeDocumentDownloadView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, employee_id, doc_id):
        organisation = get_active_admin_organisation(request, request.user)
        document = get_object_or_404(
            Document,
            employee_id=employee_id,
            employee__organisation=organisation,
            id=doc_id,
        )
        return Response({'url': generate_download_url(document, accessed_by=request.user, request=request, access_context='ORG_ADMIN')})


class EmployeeDocumentVerifyView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, employee_id, doc_id):
        organisation = get_active_admin_organisation(request, request.user)
        document = get_object_or_404(
            Document,
            employee_id=employee_id,
            employee__organisation=organisation,
            id=doc_id,
        )
        try:
            document = verify_document(document, request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DocumentSerializer(document).data)


class EmployeeDocumentRejectView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, employee_id, doc_id):
        organisation = get_active_admin_organisation(request, request.user)
        document = get_object_or_404(
            Document,
            employee_id=employee_id,
            employee__organisation=organisation,
            id=doc_id,
        )
        serializer = RejectDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = reject_document(document, request.user, serializer.validated_data['note'])
        return Response(DocumentSerializer(document).data)


class MyDocumentListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]
    throttle_scope = 'document_upload'

    def get(self, request):
        employee = get_active_employee(request, request.user)
        return Response(DocumentSerializer(list_documents(employee), many=True).data)

    def post(self, request):
        employee = get_active_employee(request, request.user)
        serializer = LegacyUploadDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = upload_document(
                employee,
                serializer.validated_data['file'],
                serializer.validated_data['document_type'],
                uploaded_by=request.user,
                metadata=serializer.validated_data.get('metadata'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class MyDocumentRequestListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = get_active_employee(request, request.user)
        return Response(EmployeeDocumentRequestSerializer(list_document_requests(employee), many=True).data)


class MyDocumentRequestUploadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]
    throttle_scope = 'document_upload'

    def post(self, request, request_id):
        employee = get_active_employee(request, request.user)
        serializer = UploadRequestedDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_request = get_object_or_404(EmployeeDocumentRequest, employee=employee, id=request_id)
        try:
            document = upload_document_request(
                employee,
                document_request,
                serializer.validated_data['file'],
                uploaded_by=request.user,
                metadata=serializer.validated_data.get('metadata'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class MyDocumentDownloadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, doc_id):
        employee = get_active_employee(request, request.user)
        document = get_object_or_404(Document, employee=employee, id=doc_id)
        return Response({'url': generate_download_url(document, accessed_by=request.user, request=request, access_context='EMPLOYEE_SELF')})
