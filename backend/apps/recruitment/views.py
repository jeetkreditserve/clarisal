from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.employees.serializers import EmployeeListSerializer
from apps.locations.models import OfficeLocation

from .models import Application, ApplicationStage, Candidate, Interview, JobPosting, OfferLetter, OfferStatus
from .serializers import (
    ApplicationSerializer,
    ApplicationStageUpdateSerializer,
    CandidateDetailSerializer,
    InterviewSerializer,
    InterviewWriteSerializer,
    JobPostingSerializer,
    JobPostingWriteSerializer,
    OfferLetterSerializer,
    OfferLetterWriteSerializer,
)
from .services import (
    accept_offer_and_onboard,
    advance_application_stage,
    convert_candidate_to_employee,
    create_job_posting,
    create_offer_letter,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_department(organisation, department_id):
    if not department_id:
        return None
    return get_object_or_404(Department, organisation=organisation, id=department_id, is_active=True)


def _get_location(organisation, location_id):
    if not location_id:
        return None
    return get_object_or_404(OfficeLocation, organisation=organisation, id=location_id, is_active=True)


def _get_interviewer(organisation, interviewer_id):
    if not interviewer_id:
        return None
    return get_object_or_404(Employee, organisation=organisation, id=interviewer_id)


class OrgJobPostingListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        postings = (
            JobPosting.objects.filter(organisation=organisation)
            .select_related('department', 'location')
            .annotate(application_count=Count('applications'))
            .order_by('-created_at')
        )
        return Response(JobPostingSerializer(postings, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = JobPostingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        posting = create_job_posting(
            organisation=organisation,
            title=data['title'],
            description=data.get('description', ''),
            requirements=data.get('requirements', ''),
            department=_get_department(organisation, data.get('department_id')),
            location=_get_location(organisation, data.get('location_id')),
            closes_at=data.get('closes_at'),
            actor=request.user,
        )
        return Response(JobPostingSerializer(posting).data, status=status.HTTP_201_CREATED)


class OrgApplicationListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        stage = request.query_params.get('stage')
        queryset = (
            Application.objects.filter(job_posting__organisation=organisation)
            .select_related('candidate', 'job_posting', 'offer_letter')
            .prefetch_related(
                Prefetch('interviews', queryset=Interview.objects.select_related('interviewer__user').order_by('scheduled_at'))
            )
            .order_by('-applied_at')
        )
        if stage:
            queryset = queryset.filter(stage=stage)
        return Response(ApplicationSerializer(queryset, many=True).data)


class OrgCandidateDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        candidate = get_object_or_404(
            Candidate.objects.filter(organisation=organisation)
            .select_related('converted_to_employee__user')
            .prefetch_related(
                Prefetch(
                    'applications',
                    queryset=Application.objects.select_related('job_posting', 'offer_letter').prefetch_related(
                        Prefetch('interviews', queryset=Interview.objects.select_related('interviewer__user').order_by('scheduled_at'))
                    ),
                )
            ),
            id=pk,
        )
        return Response(CandidateDetailSerializer(candidate).data)


class OrgCandidateConvertView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        candidate = get_object_or_404(
            Candidate.objects.select_related('converted_to_employee__user').filter(organisation=organisation),
            id=pk,
        )
        offer = (
            OfferLetter.objects.filter(
                application__candidate=candidate,
                application__job_posting__organisation=organisation,
                status=OfferStatus.ACCEPTED,
            )
            .select_related('application__candidate', 'onboarded_employee__user')
            .order_by('-accepted_at', '-created_at')
            .first()
        )
        if offer is None:
            return Response({'error': 'Accepted offer not found for this candidate.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = convert_candidate_to_employee(candidate, offer, actor=request.user)
        except ValueError as exc:
            message = str(exc)
            if message == 'Candidate has already been converted to an employee.':
                return Response({'error': message}, status=status.HTTP_409_CONFLICT)
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'employee': EmployeeListSerializer(employee).data,
                'message': f'Candidate converted to employee invite for {employee.user.email}',
            },
            status=status.HTTP_201_CREATED,
        )


class OrgApplicationStageView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        application = get_object_or_404(Application, id=pk, job_posting__organisation=organisation)
        serializer = ApplicationStageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = advance_application_stage(application, serializer.validated_data['stage'], actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationSerializer(application).data)


class OrgInterviewListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request, application_id):
        organisation = _get_admin_organisation(request)
        application = get_object_or_404(Application, id=application_id, job_posting__organisation=organisation)
        interviews = application.interviews.select_related('interviewer__user').order_by('scheduled_at')
        return Response(InterviewSerializer(interviews, many=True).data)

    def post(self, request, application_id):
        organisation = _get_admin_organisation(request)
        application = get_object_or_404(Application, id=application_id, job_posting__organisation=organisation)
        serializer = InterviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        interview = Interview.objects.create(
            application=application,
            interviewer=_get_interviewer(organisation, data.get('interviewer_id')),
            scheduled_at=data['scheduled_at'],
            format=data.get('format'),
            feedback=data.get('feedback', ''),
            meet_link=data.get('meet_link', ''),
            created_by=request.user,
            modified_by=request.user,
        )
        if application.stage != ApplicationStage.INTERVIEW:
            application.stage = ApplicationStage.INTERVIEW
            application.modified_by = request.user
            application.save(update_fields=['stage', 'modified_at', 'modified_by'])
        return Response(InterviewSerializer(interview).data, status=status.HTTP_201_CREATED)


class OrgOfferLetterView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, application_id):
        organisation = _get_admin_organisation(request)
        application = get_object_or_404(Application, id=application_id, job_posting__organisation=organisation)
        serializer = OfferLetterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            offer = create_offer_letter(
                application=application,
                ctc_annual=data['ctc_annual'],
                joining_date=data.get('joining_date'),
                template_text=data.get('template_text', ''),
                expires_at=data.get('expires_at'),
                actor=request.user,
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OfferLetterSerializer(offer).data, status=status.HTTP_201_CREATED)


class OrgOfferAcceptView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        offer = get_object_or_404(OfferLetter, id=pk, application__job_posting__organisation=organisation)
        try:
            employee = accept_offer_and_onboard(offer, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'employee_id': str(employee.id), 'status': employee.status})
