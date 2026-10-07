from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404,render,redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Decision,DecisionUpdate,Meeting,Membership,Notification
from .permissions import active_context,available_contexts
from .meetings_service import meeting_access

def access(context,obj):
    if not context or not available_contexts(context.user).filter(pk=context.pk).exists():return False
    return meeting_access(context,'private',obj.vote.meeting) or context.organization_id==obj.vote.meeting.organization_id and context.user_id==obj.responsible_id and context.role in ('author','reviewer','clerk')

@transaction.atomic
def update(context,decision_id,version,action,progress='',responsible=None,due_on=None):
    initial=Decision.objects.select_related('vote__meeting').get(pk=decision_id)
    meeting=Meeting.objects.select_for_update().get(pk=initial.vote.meeting_id)
    obj=Decision.objects.select_for_update().select_related('vote__meeting').get(pk=decision_id)
    if settings.SERVER_ROLE!='internal' or meeting.leading_server!='internal' or meeting.state=='return_pending' or not access(context,obj):raise PermissionDenied
    manager=meeting_access(context,'protocol',meeting)
    if obj.version!=version:raise ValidationError('Sachstand wurde geändert; bitte Ihre Eingabe mit aktuellem Stand vergleichen.')
    if not isinstance(progress,str) or len(progress)>100000:raise ValidationError('Sachstand zu groß.')
    if action=='assign':
        if not manager:raise PermissionDenied
        if responsible and not any(c.organization_id==meeting.organization_id and c.role in ('author','reviewer','clerk') for c in available_contexts(responsible)):raise ValidationError('Zuständigkeit benötigt ein aktuelles Verwaltungskonto in dieser Körperschaft.')
        obj.responsible=responsible;obj.due_on=due_on;obj.status='open'
        if responsible:Notification.objects.create(user=responsible,text='Eine Beschlussaufgabe wurde Ihnen zugewiesen.',path=f'/beschluesse/{obj.pk}/')
    elif action in ('progress','complete'):
        if not manager and context.user_id!=obj.responsible_id:raise PermissionDenied
        if obj.status in ('closed','not_required'):raise ValidationError('Vorgang zuerst ausdrücklich wieder eröffnen.')
        obj.progress=progress;obj.status='reported' if action=='complete' else 'in_progress'
    elif action in ('close','reopen','not_required'):
        if not manager or not progress.strip():raise PermissionDenied
        if action=='close' and obj.status!='reported':raise ValidationError('Zuerst Erledigung melden lassen.')
        obj.status={'close':'closed','reopen':'open','not_required':'not_required'}[action];obj.progress=progress
    else:raise ValidationError('Unbekannte Beschlussaktion.')
    obj.version+=1;obj.save();meeting.version+=1;meeting.save(update_fields=['version'])
    DecisionUpdate.objects.create(decision=obj,version=obj.version,snapshot={'status':obj.status,'progress':obj.progress,'responsible_id':str(obj.responsible_id) if obj.responsible_id else None,'due_on':obj.due_on.isoformat() if obj.due_on else None,'action':action},actor=context.user)
    return obj

@login_required
@require_http_methods(['GET'])
def index(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    rows=[d for d in Decision.objects.select_related('vote__meeting','responsible').filter(vote__meeting__organization=context.organization) if access(context,d)]
    state=request.GET.get('state','');query=request.GET.get('q','')[:100]
    rows=[d for d in rows if (not state or d.status==state) and query.casefold() in d.wording.casefold()]
    for d in rows:d.overdue=bool(d.due_on and d.due_on<timezone.localdate() and d.status not in ('closed','not_required'))
    return render(request,'decisions.html',{'context':context,'objects':rows,'query':query,'state':state})

@login_required
@require_http_methods(['GET','POST'])
def detail(request,decision_id):
    obj=get_object_or_404(Decision.objects.select_related('vote__meeting','responsible'),pk=decision_id);context=active_context(request)
    if not access(context,obj):raise PermissionDenied
    error=None;pending=None
    if request.method=='POST':
        try:
            responsible=None
            if request.POST.get('responsible'):responsible=get_object_or_404(Membership,pk=request.POST['responsible'],organization=obj.vote.meeting.organization).user
            due_on=None
            if request.POST.get('due_on'):
                from datetime import date
                due_on=date.fromisoformat(request.POST['due_on'])
            pending=request.POST.get('progress','');update(context,obj.pk,int(request.POST.get('version',0)),request.POST.get('action'),pending,responsible,due_on)
        except (ValidationError,ValueError) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Frist und Fassung prüfen.'
        else:return redirect('decision',decision_id=obj.pk)
    return render(request,'decision.html',{'context':context,'obj':obj,'manager':meeting_access(context,'protocol',obj.vote.meeting),'memberships':Membership.objects.filter(organization=obj.vote.meeting.organization,role__in=['author','reviewer','clerk']),'error':error,'progress':pending if error else obj.progress})
