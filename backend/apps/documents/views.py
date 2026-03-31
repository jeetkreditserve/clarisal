from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin
from apps.employees.models import Employee

from .models import Document
from .repositories import list_documents
from .serializers import DocumentSerializer, RejectDocumentSerializer, UploadDocumentSerializer
from .services import generate_download_url, reject_document, upload_document, verify_document


class EmployeeDocumentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        return Response(DocumentSerializer(list_documents(employee), many=True).data)

    def post(self, request, employee_id):
        organisation = get_active_admin_organisation(request, request.user)
        employee = get_object_or_404(Employee, organisation=organisation, id=employee_id)
        serializer = UploadDocumentSerializer(data=request.data)
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


class EmployeeDocumentDownloadView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, employee_id, doc_id):
        organisation = get_active_admin_organisation(request, request.user)
        document = get_object_or_404(
            Document,
            employee_id=employee_id,
            employee__organisation=organisation,
            id=doc_id,
        )
        return Response({'url': generate_download_url(document)})


class EmployeeDocumentVerifyView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

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
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

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

    def get(self, request):
        employee = get_active_employee(request, request.user)
        return Response(DocumentSerializer(list_documents(employee), many=True).data)

    def post(self, request):
        employee = get_active_employee(request, request.user)
        serializer = UploadDocumentSerializer(data=request.data)
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


class MyDocumentDownloadView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, doc_id):
        employee = get_active_employee(request, request.user)
        document = get_object_or_404(Document, employee=employee, id=doc_id)
        return Response({'url': generate_download_url(document)})
