from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404,redirect
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST
from .models import MeetingInvitation,InvitationDelivery,ReplicaAsset
from .permissions import active_context
from .meetings_service import meeting_access
from .invitation_packets import packet,calendar

@login_required
@require_GET
def download(request,invitation_id,format):
    invitation=get_object_or_404(MeetingInvitation.objects.select_related('meeting'),pk=invitation_id)
    context=active_context(request)
    if not meeting_access(context,'export',invitation.meeting):raise PermissionDenied
    delivery=InvitationDelivery.objects.filter(invitation=invitation,user=request.user).first()
    if delivery:
        if str(context.pk)!=delivery.snapshot.get('context_id'):raise PermissionDenied('Bitte den in der Einladung ausgewählten Arbeitskontext verwenden.')
        data=delivery.snapshot
    elif meeting_access(context,'plan',invitation.meeting):data=invitation.snapshot
    else:raise PermissionDenied
    if format=='ics':binary=calendar(data);mime='text/calendar; charset=utf-8'
    elif format=='pdf':binary=packet(data,context);mime='application/pdf'
    else:raise Http404
    response=HttpResponse(binary,content_type=mime);response['Content-Disposition']=f'attachment; filename="sitzung-{invitation.meeting_id}-r{invitation.revision}.{format}"';return response

@login_required
@require_POST
def seen(request,delivery_id):
    delivery=get_object_or_404(InvitationDelivery,pk=delivery_id,user=request.user)
    if not meeting_access(active_context(request),'read',delivery.invitation.meeting):raise PermissionDenied
    delivery.seen_at=timezone.now();delivery.save(update_fields=['seen_at']);return redirect('meeting_detail',meeting_id=delivery.invitation.meeting_id)
