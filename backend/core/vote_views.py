import uuid
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.shortcuts import get_object_or_404,render,redirect
from django.views.decorators.http import require_http_methods
from .models import Vote,Meeting
from .permissions import active_context
from .meetings_service import meeting_access
from .live_views import device
from . import voting

@login_required
@require_http_methods(['GET','POST'])
def workspace(request,meeting_id):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'private',obj):raise PermissionDenied
    error=None
    if request.method=='POST':
        try:
            action=request.POST.get('action');version=int(request.POST.get('expected_version',0));epoch=int(request.POST.get('epoch',0))
            if action=='open':voting.open_vote(context,obj.pk,version,device(request),epoch,request.POST.get('wording',''),request.POST.get('mode'),request.POST.get('rule'),request.POST.get('options','Ja\nNein\nEnthaltung').splitlines())
            else:
                vote=get_object_or_404(Vote,pk=request.POST.get('vote_id'),meeting=obj)
                if action=='cast':voting.cast(context,vote.pk,request.POST.get('choice'),uuid.UUID(request.POST.get('request_id','')))
                elif action=='confirm':voting.confirm(context,vote.pk,version,device(request),epoch,request.POST.get('wording',''),request.POST.get('reason',''))
                elif action in ('close','abort'):
                    counts={option:int(request.POST.get('count_'+str(n),0)) for n,option in enumerate(vote.options)}
                    voting.finish(context,vote.pk,version,device(request),epoch,counts,int(request.POST.get('invalid',0)),action=='abort')
                else:raise ValidationError('Unbekannte Aktion.')
        except (ValidationError,ValueError) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Zahlen und Stimm-ID prüfen.'
        else:return redirect('votes',meeting_id=obj.pk)
    obj.refresh_from_db()
    from .models import MeetingLease
    from django.utils import timezone
    lease=MeetingLease.objects.filter(meeting=obj,holder=request.user,device=device(request),context_id=context.pk,expires_at__gt=timezone.now()).first()
    writer=bool(lease and meeting_access(context,'live',obj))
    votes=list(obj.votes.select_related('item').order_by('-created_at'))
    for vote in votes:
        vote.may_cast=bool(vote.state=='open' and vote.mode=='named' and voting.eligible(context,vote) and not vote.ballots.filter(participant__user=request.user).exists())
        vote.count_fields=list(enumerate(vote.options));vote.ballot_count=vote.ballots.count()
    return render(request,'votes.html',{'context':context,'obj':obj,'votes':votes,'writer':writer,'epoch':lease.epoch if lease else 0,'error':error,'request_id':uuid.uuid4()})
