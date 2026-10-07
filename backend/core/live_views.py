import json,uuid
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import get_object_or_404,render,redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_POST
from .models import Meeting,MeetingLease,MeetingEvent,AgendaItem,MeetingParticipant,ConflictOfInterest,ItemNote,Motion
from .permissions import active_context
from .meetings_service import meeting_access
from .live_service import activate,claim,renew,roster,write,quorum

class ActivationForm(forms.Form):
    server=forms.ChoiceField(label='Führender Sitzungsserver',choices=[('protected','Geschützter externer Server'),('internal','Interner Server')])
    quorum=forms.ChoiceField(label='Beschlussfähigkeitsregel',choices=[('majority_statutory','Mehr als die Hälfte der gesetzlichen Mitgliederzahl'),('majority_nonexcluded','Mehr als die Hälfte nach Abzug festgestellter Ausschlüsse'),('repeated_minimum','Wiederholungssitzung: konfigurierte Mindestzahl'),('manual','Nur manuelle Feststellung')])
    minimum=forms.IntegerField(label='Mindestzahl bei Wiederholungssitzung',min_value=1,max_value=1000,initial=3)
    statutory_confirmed=forms.BooleanField(label='Gesetzliche Mitgliederzahl und Regelprofil fachlich geprüft; Sondervoraussetzungen sind dokumentiert')
    expected_version=forms.IntegerField(widget=forms.HiddenInput)

@login_required
@require_http_methods(['GET','POST'])
def activation(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if settings.SERVER_ROLE!='internal' or not meeting_access(context,'invite',obj):raise PermissionDenied
    form=ActivationForm(request.POST if request.method=='POST' else None,initial={'expected_version':obj.version,'quorum':'majority_statutory'})
    if request.method=='POST' and form.is_valid():
        try:activate(context,obj.pk,form.cleaned_data['expected_version'],form.cleaned_data['server'],{'quorum':form.cleaned_data['quorum'],'minimum':form.cleaned_data['minimum'],'confirmed':True})
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:messages.success(request,'Führerschaft festgelegt. Bei externer Führung vor Beginn die erfolgreiche Übertragung prüfen.');return redirect('meeting_detail',meeting_id=obj.pk)
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Sitzungsführung aktivieren'})

def device(request):
    if not request.session.get('live_device'):request.session['live_device']=str(uuid.uuid4())
    return uuid.UUID(request.session['live_device'])

@login_required
@require_http_methods(['GET','POST'])
def workspace(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting.objects.select_related('committee','chair','scribe'),pk=meeting_id)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    error=None;pending_text=None
    if request.method=='POST':
        try:
            kind=request.POST.get('kind');version=int(request.POST.get('expected_version',0));epoch=int(request.POST.get('epoch',0));client=device(request)
            if kind=='claim':claim(context,obj.pk,version,client,request.POST.get('reason',''))
            elif kind=='roster':roster(context,obj.pk,version,client,epoch)
            else:
                data={}
                if request.POST.get('item_id'):data['item_id']=request.POST['item_id']
                if kind=='presence':data.update(participant_id=request.POST.get('participant_id'),present=request.POST.get('present')=='true')
                elif kind=='conflict':data.update(participant_id=request.POST.get('participant_id'),active=request.POST.get('active')=='true',reason=request.POST.get('reason',''))
                elif kind=='text':data['markdown']=request.POST.get('markdown','');pending_text=data['markdown']
                elif kind=='motion':data.update(applicant=request.POST.get('applicant',''),wording=request.POST.get('wording',''),kind=request.POST.get('motion_kind'),position=int(request.POST.get('position',1)))
                elif kind=='quorum':data.update(confirmed=request.POST.get('confirmed')=='true',reason=request.POST.get('reason',''))
                event_id=uuid.UUID(request.POST.get('event_id',''))
                write(context,obj.pk,version,client,epoch,kind,data,event_id,request.POST.get('occurred_at') or None)
        except (ValidationError,ValueError,KeyError,ObjectDoesNotExist) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Eingabe oder Ausgangsstand ungültig. Bitte prüfen.'
        else:return redirect('live_workspace',meeting_id=obj.pk)
    obj.refresh_from_db()
    lease=MeetingLease.objects.filter(meeting=obj,holder=request.user,device=device(request),context_id=context.pk,expires_at__gt=timezone.now()).first()
    writer=bool(lease and obj.leading_server==settings.SERVER_ROLE and meeting_access(context,'live',obj))
    private=meeting_access(context,'private',obj)
    if not private and obj.active_item and not obj.active_item.public:obj.active_item=None
    people=list(obj.roster.select_related('user','person','substitutes_for'))
    conflicts=ConflictOfInterest.objects.filter(item=obj.active_item,active=True).values_list('participant_id',flat=True) if obj.active_item_id else []
    if not private:people=[]
    for person in people:person.conflicted=person.pk in conflicts
    note=ItemNote.objects.filter(item=obj.active_item).first() if obj.active_item_id else None
    items=obj.items.filter(removed=False)
    if not meeting_access(context,'private',obj):items=items.filter(public=True)
    events=obj.events.order_by('-version')
    if not meeting_access(context,'private',obj):events=events.filter(item__public=True)
    return render(request,'live_workspace.html',{'context':context,'obj':obj,'items':items,'people':people,'writer':writer,'epoch':lease.epoch if lease else 0,'can_claim':obj.leading_server==settings.SERVER_ROLE and request.user.pk in (obj.chair_id,obj.scribe_id),'quorum':quorum(obj,obj.active_item) if private else {'present':'nicht freigegeben','required':None,'calculated':None},'note':pending_text if error and pending_text is not None else note.markdown if note else '', 'events':events[:100],'motions':Motion.objects.filter(item=obj.active_item).order_by('position') if obj.active_item_id else [],'error':error,'event_id':uuid.uuid4()})

@login_required
@require_POST
def heartbeat(request,meeting_id):
    try:version=renew(active_context(request),meeting_id,device(request),int(request.POST.get('epoch',0)))
    except (ValidationError,ValueError,PermissionDenied):return JsonResponse({'error':'authority-expired'},status=409)
    return JsonResponse({'version':version})

@login_required
@require_http_methods(['GET'])
def status(request,meeting_id):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    return JsonResponse({'version':obj.version,'state':obj.state,'paused':obj.paused,'active_item':str(obj.active_item_id) if obj.active_item_id and (meeting_access(context,'private',obj) or obj.active_item.public) else None,'quorum':quorum(obj,obj.active_item) if meeting_access(context,'private',obj) else None})
