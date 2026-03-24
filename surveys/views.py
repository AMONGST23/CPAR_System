from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import MaternalRecordForm
from .models import MaternalRecord, SyncLog
from .utils import SyncConfigurationError, sync_unsynced_records

SECTION_SEQUENCE = ['sec-a', 'sec-b', 'sec-c', 'sec-d', 'sec-e', 'sec-f', 'sec-g', 'sec-h', 'sec-i', 'sec-j', 'sec-k']


def _normalize_section(section_name):
    return section_name if section_name in SECTION_SEQUENCE else SECTION_SEQUENCE[0]


def _next_section(current_section):
    normalized = _normalize_section(current_section)
    index = SECTION_SEQUENCE.index(normalized)
    if index >= len(SECTION_SEQUENCE) - 1:
        return normalized
    return SECTION_SEQUENCE[index + 1]


@login_required
def record_list(request):
    records_source = list(MaternalRecord.objects.select_related('agent').all())
    q = request.GET.get('q', '').strip()
    if q:
        needle = q.lower()
        records_source = [
            record for record in records_source
            if needle in (record.last_name or '').lower()
            or needle in (record.first_name or '').lower()
            or needle in (record.address_barangay or '').lower()
        ]

    paginator = Paginator(records_source, 20)
    page = request.GET.get('page', 1)
    records = paginator.get_page(page)
    unsynced_count = MaternalRecord.objects.filter(is_synced=False).count()
    last_sync = SyncLog.objects.first()
    system_status = {
        'encryption_configured': bool(getattr(settings, 'FIELD_ENCRYPTION_KEY', '')),
        'local_storage_ready': True,
    }
    return render(request, 'surveys/list.html', {
        'records': records,
        'q': q,
        'unsynced_count': unsynced_count,
        'last_sync': last_sync,
        'system_status': system_status,
    })


@login_required
def record_create(request):
    active_section = _normalize_section(request.GET.get('section'))
    if request.method == 'POST':
        form = MaternalRecordForm(request.POST)
        active_section = _normalize_section(request.POST.get('current_section'))
        if form.is_valid():
            record = form.save(commit=False)
            record.agent = request.user
            record.is_synced = True
            record.save()
            submit_action = request.POST.get('submit_action', 'continue')
            if submit_action == 'exit':
                messages.success(request, f'Record for {record.full_name} saved successfully.')
                return redirect('record_list')

            next_section = _next_section(active_section)
            if next_section == active_section:
                messages.success(request, f'Record for {record.full_name} saved successfully.')
                return redirect('record_detail', pk=record.pk)

            messages.success(request, 'Section saved. Continue with the next section.')
            return redirect(f"{reverse('record_edit', kwargs={'pk': record.pk})}?section={next_section}")
    else:
        form = MaternalRecordForm()
    return render(request, 'surveys/form.html', {
        'form': form,
        'action': 'New',
        'active_section': active_section,
        'section_sequence': SECTION_SEQUENCE,
    })


@login_required
def record_detail(request, pk):
    record = get_object_or_404(MaternalRecord, pk=pk)
    return render(request, 'surveys/detail.html', {'record': record})


@login_required
def record_edit(request, pk):
    record = get_object_or_404(MaternalRecord, pk=pk)
    active_section = _normalize_section(request.GET.get('section'))
    if request.method == 'POST':
        form = MaternalRecordForm(request.POST, instance=record)
        active_section = _normalize_section(request.POST.get('current_section'))
        if form.is_valid():
            updated = form.save(commit=False)
            updated.is_synced = True
            updated.save()
            submit_action = request.POST.get('submit_action', 'continue')
            if submit_action == 'exit':
                messages.success(request, 'Record updated successfully.')
                return redirect('record_detail', pk=record.pk)

            next_section = _next_section(active_section)
            if next_section == active_section:
                messages.success(request, 'Record updated successfully.')
                return redirect('record_detail', pk=record.pk)

            messages.success(request, 'Section saved. Continue with the next section.')
            return redirect(f"{reverse('record_edit', kwargs={'pk': record.pk})}?section={next_section}")
    else:
        form = MaternalRecordForm(instance=record)
    return render(request, 'surveys/form.html', {
        'form': form,
        'record': record,
        'action': 'Edit',
        'active_section': active_section,
        'section_sequence': SECTION_SEQUENCE,
    })


@login_required
def record_delete(request, pk):
    record = get_object_or_404(MaternalRecord, pk=pk)
    if request.method == 'POST':
        name = record.full_name
        record.delete()
        messages.success(request, f'Record for {name} deleted.')
        return redirect('record_list')
    return render(request, 'surveys/confirm_delete.html', {'record': record})


@login_required
@require_POST
def trigger_sync(request):
    try:
        result = sync_unsynced_records()
    except SyncConfigurationError as error:
        return JsonResponse({'status': 'error', 'message': str(error)}, status=400)

    status_code = 200 if result['status'] in ['ok', 'partial'] else 500
    return JsonResponse({
        'status': result['status'],
        'message': result['message'],
        'count': result['synced'],
        'failed': result['failed'],
        'attempted': result['attempted'],
    }, status=status_code)
