import json
from secrets import compare_digest
from urllib.parse import parse_qs

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation

from .models import BiometricDevice, BiometricSyncLog
from .protocols.adms import handle_adms_push
from .protocols.essl_ebioserver import handle_essl_ebioserver_push
from .serializers import BiometricDeviceSerializer, BiometricDeviceWriteSerializer, BiometricSyncLogSerializer


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


@method_decorator(csrf_exempt, name='dispatch')
class AdmsCdataView(View):
    def get(self, request):
        serial = request.GET.get('SN', '')
        now = timezone.now()
        response_body = (
            f'GET OPTION FROM: {serial}\n'
            f'ATTLOGStamp={int(now.timestamp())}\n'
            f'OPERLOGStamp=9999\n'
            f'ATTPHOTOStamp=None\n'
            f'ErrorDelay=30\n'
            f'Delay=10\n'
            f'TransTimes=00:00;14:05\n'
            f'TransInterval=1\n'
            f'TransFlag=TransData AttLog\n'
            f'TimeZone=5.5\n'
            f'Realtime=1\n'
            f'Encrypt=None\n'
        )
        return HttpResponse(response_body, content_type='text/plain')

    def post(self, request):
        serial = request.GET.get('SN', '')
        if request.GET.get('table', '') != 'ATTLOG':
            return HttpResponse('OK', content_type='text/plain')

        device = BiometricDevice.objects.select_related('organisation').filter(
            device_serial=serial,
            is_active=True,
        ).first()
        if device is None:
            return HttpResponse('OK', content_type='text/plain')

        summary = handle_adms_push(
            body=request.body.decode('utf-8', errors='replace'),
            organisation_id=str(device.organisation_id),
            device_serial=serial,
        )
        BiometricSyncLog.objects.create(
            device=device,
            records_fetched=summary['processed'] + summary['skipped'],
            records_processed=summary['processed'],
            records_skipped=summary['skipped'],
            errors=summary['errors'],
            success=not summary['errors'],
        )
        device.last_sync_at = timezone.now()
        device.save(update_fields=['last_sync_at', 'modified_at'])
        return HttpResponse('OK', content_type='text/plain')


def _load_push_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return {}
    if request.POST:
        payload = request.POST.dict()
        for key in ('transactions', 'logs', 'events', 'data', 'payload'):
            raw = payload.get(key)
            if raw:
                try:
                    payload[key] = json.loads(raw)
                except json.JSONDecodeError:
                    pass
        return payload
    if request.body:
        parsed = parse_qs(request.body.decode('utf-8'), keep_blank_values=True)
        return {key: values[0] if len(values) == 1 else values for key, values in parsed.items()}
    return {}


def _get_push_secret(payload, request):
    header_secret = request.headers.get('X-Biometric-Secret', '')
    if header_secret:
        return header_secret
    if isinstance(payload, dict):
        realtime_payload = payload.get('RealTime')
        if isinstance(realtime_payload, dict):
            return str(realtime_payload.get('AuthToken') or realtime_payload.get('auth_token') or '').strip()
        return str(payload.get('AuthToken') or payload.get('auth_token') or '').strip()
    return ''


@method_decorator(csrf_exempt, name='dispatch')
class EsslEbioserverEventsView(View):
    def post(self, request, device_id):
        device = BiometricDevice.objects.select_related('organisation').filter(
            id=device_id,
            protocol='ESSL_EBIOSERVER',
            is_active=True,
        ).first()
        if device is None:
            return HttpResponse(status=404)

        payload = _load_push_payload(request)
        provided_secret = _get_push_secret(payload, request)
        stored_secret = device.get_api_key() if device.api_key_encrypted else ''
        if not stored_secret or not compare_digest(provided_secret, stored_secret):
            return HttpResponse('Forbidden', status=403, content_type='text/plain')

        summary = handle_essl_ebioserver_push(
            payload=payload,
            organisation_id=str(device.organisation_id),
            device_id=str(device.id),
        )
        BiometricSyncLog.objects.create(
            device=device,
            records_fetched=summary['processed'] + summary['skipped'] + len(summary['errors']),
            records_processed=summary['processed'],
            records_skipped=summary['skipped'],
            errors=summary['errors'],
            success=not summary['errors'],
        )
        device.last_sync_at = timezone.now()
        device.save(update_fields=['last_sync_at', 'modified_at'])
        return HttpResponse(
            json.dumps(summary),
            content_type='application/json',
        )


class BiometricDeviceListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        devices = BiometricDevice.objects.filter(organisation=organisation).order_by('name')
        return Response(BiometricDeviceSerializer(devices, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = BiometricDeviceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.save(organisation=organisation)
        return Response(BiometricDeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class BiometricDeviceDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        serializer = BiometricDeviceWriteSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        return Response(BiometricDeviceSerializer(device).data)

    def delete(self, request, pk):
        organisation = _get_admin_organisation(request)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        device.is_active = False
        device.save(update_fields=['is_active', 'modified_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class BiometricSyncLogListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        device = get_object_or_404(BiometricDevice, organisation=organisation, id=pk)
        logs = device.sync_logs.order_by('-synced_at')[:50]
        return Response(BiometricSyncLogSerializer(logs, many=True).data)
