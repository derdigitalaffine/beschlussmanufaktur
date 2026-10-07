from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_POST
from .models import Meeting,AgendaItem,MeetingInvitation,InvitationDelivery,MeetingAmendment,MeetingGuest,Membership,RegistryRecord,Template,AuditEvent,User
from .permissions import active_context,available_contexts
from .meetings_service import meeting_access,lock_meeting,save_item,issue,approve_amendment,meeting_snapshot,paper_markdown
from .templates_service import template_access
from .document_export import export

class MeetingForm(forms.ModelForm):
    expected_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    class Meta:
        model=Meeting
        fields=['committee','title','starts_at','ends_at','room','location','chair','scribe','statutory_count','invitation_days','proposal_deadline','release_deadline','public_notice','public_enabled']
        labels={'committee':'Gremium','title':'Sitzungsbezeichnung','starts_at':'Beginn','ends_at':'Geplantes Ende','room':'Raum','location':'Ort / Adresse','chair':'Vorsitz','scribe':'Schriftführung','statutory_count':'Gesetzliche Mitgliederzahl','invitation_days':'Volle Kalendertage Einladungsfrist','proposal_deadline':'Vorlagenschluss','release_deadline':'Freigabeschluss','public_notice':'Öffentliche Bekanntmachung','public_enabled':'Bekanntmachung öffentlich bereitstellen'}
        widgets={x:forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M') for x in ['starts_at','ends_at','proposal_deadline','release_deadline']}
    def __init__(self,*args,organization,**kwargs):
        super().__init__(*args,**kwargs);self.instance.organization=organization
        self.fields['committee'].queryset=RegistryRecord.objects.filter(organization=organization,kind='committee',archived=False)
        self.fields['room'].queryset=RegistryRecord.objects.filter(organization=organization,kind='room',archived=False)
        people=User.objects.filter(pk__in=Membership.objects.filter(organization=organization).values('user_id'))
        self.fields['chair'].queryset=people.filter(memberships__organization=organization,memberships__role__in=['chair','mayor','local_mayor'],memberships__revoked_at__isnull=True,is_active=True).distinct()
        self.fields['scribe'].queryset=people.filter(memberships__organization=organization,memberships__role='clerk',memberships__revoked_at__isnull=True,is_active=True).distinct()
        self.fields['invitation_days'].max_value=60
        self.fields['statutory_count'].max_value=1000

class AgendaForm(forms.ModelForm):
    expected_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    class Meta:
        model=AgendaItem
        fields=['position','parent','title','public_title','public','template','markdown','estimated_minutes','removed']
        labels={'position':'Reihenfolge','parent':'Unterpunkt zu','title':'Interner / öffentlicher Betreff','public_title':'Unverfänglicher Bekanntmachungstitel bei nichtöffentlichem TOP','public':'Öffentlicher Teil','template':'Bereitgestellte Vorlage','markdown':'Weitere Sitzungsunterlage (Markdown)','estimated_minutes':'Geplante Minuten','removed':'Im Entwurf entfernen'}
    def __init__(self,*args,meeting,context,**kwargs):
        super().__init__(*args,**kwargs);self.instance.meeting=meeting;self.instance.proposed_by=context.user
        self.fields['parent'].queryset=AgendaItem.objects.filter(meeting=meeting,removed=False).exclude(pk=self.instance.pk)
        ids=[t.pk for t in Template.objects.filter(state='ready').select_related('kind','organization','unit') if template_access(context,'read',t)]
        self.fields['template'].queryset=Template.objects.filter(pk__in=ids)

@login_required
@require_http_methods(['GET'])
def index(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    meetings=[m for m in Meeting.objects.filter(organization=context.organization).select_related('committee','chair','scribe') if meeting_access(context,'read',m)]
    return render(request,'meetings.html',{'context':context,'meetings':meetings,'can_plan':context.role=='clerk'})

@login_required
@require_http_methods(['GET','POST'])
def edit(request,meeting_id=None):
    context=active_context(request)
    if not context:raise PermissionDenied
    if not meeting_id and context.role!='clerk':raise PermissionDenied
    obj=get_object_or_404(Meeting,pk=meeting_id,organization=context.organization) if meeting_id else Meeting(organization=context.organization,created_by=request.user)
    if meeting_id and not meeting_access(context,'plan',obj):raise PermissionDenied
    form=MeetingForm(request.POST if request.method=='POST' else None,organization=context.organization,instance=obj,initial={'expected_version':obj.version})
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                if meeting_id:
                    old=lock_meeting(context,meeting_id,'plan',form.cleaned_data['expected_version'])
                    if old.state!='preparation':raise ValidationError('Nach Einladung nur dokumentierte Nachträge verwenden.')
                    form.instance.version=old.version+1
                elif not available_contexts(request.user).filter(pk=context.pk).exists():raise PermissionDenied
                saved=form.save();AuditEvent.objects.create(actor=request.user,action='meeting.planned',object_id=str(saved.pk),metadata={'version':saved.version,'committee':str(saved.committee_id),'starts_at':saved.starts_at.isoformat()})
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:return redirect('meeting_detail',meeting_id=saved.pk)
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Sitzung planen'})

@login_required
@require_http_methods(['GET'])
def detail(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    data=meeting_snapshot(obj,context)
    deliveries=InvitationDelivery.objects.filter(invitation__meeting=obj,user=request.user).select_related('invitation').order_by('-invitation__revision')
    from .member_views import remember
    remember(context,'meeting',obj.pk)
    return render(request,'meeting_detail.html',{'context':context,'obj':obj,'data':data,'can_plan':meeting_access(context,'plan',obj),'can_invite':meeting_access(context,'invite',obj),'can_chair':meeting_access(context,'chair',obj),'amendments':MeetingAmendment.objects.filter(meeting=obj) if meeting_access(context,'plan',obj) or meeting_access(context,'chair',obj) else [],'deliveries':deliveries,'memberships':Membership.objects.filter(organization=obj.organization).select_related('user')})

@login_required
@require_http_methods(['GET','POST'])
def agenda(request,meeting_id,item_id=None):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'plan',obj):raise PermissionDenied
    item=get_object_or_404(AgendaItem,pk=item_id,meeting=obj) if item_id else AgendaItem(meeting=obj,proposed_by=request.user)
    form=AgendaForm(request.POST if request.method=='POST' else None,meeting=obj,context=context,instance=item,initial={'expected_version':obj.version})
    if request.method=='POST' and form.is_valid():
        try:save_item(context,obj.pk,form.cleaned_data['expected_version'],{name:form.cleaned_data[name] for name in form.Meta.fields},item.pk if item_id else None)
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:return redirect('meeting_detail',meeting_id=obj.pk)
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Tagesordnungspunkt'})

class IssueForm(forms.Form):
    expected_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    reason=forms.CharField(label='Begründung / Nachtrag / Fristausnahme',max_length=1000,required=False,widget=forms.Textarea)
    exception_confirmed=forms.BooleanField(label='Verkürzte Frist ist fachlich geprüft und durch die zuständige Stelle bestätigt',required=False)
    confirm=forms.BooleanField(label='Tagesordnung, Fassungen, Empfängerkreis und Bekanntmachung sind geprüft')

@login_required
@require_http_methods(['GET','POST'])
def invite(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'invite',obj):raise PermissionDenied
    form=IssueForm(request.POST if request.method=='POST' else None,initial={'expected_version':obj.version})
    if request.method=='POST' and form.is_valid():
        try:issue(context,obj.pk,form.cleaned_data['expected_version'],form.cleaned_data['reason'],form.cleaned_data['exception_confirmed'])
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:messages.success(request,'Einladungsstand fixiert; Versand wird im Hintergrund ausgeführt.');return redirect('meeting_detail',meeting_id=obj.pk)
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Einladung / Nachtrag ausgeben'})

class AmendmentForm(forms.Form):
    kind=forms.ChoiceField(label='Art der Änderung',choices=MeetingAmendment._meta.get_field('kind').choices)
    reason=forms.CharField(label='Begründung',max_length=1000,widget=forms.Textarea)
    title=forms.CharField(label='Neuer / berichtigter Titel',max_length=300,required=False)
    public_title=forms.CharField(label='Unverfänglicher Bekanntmachungstitel',max_length=300,required=False)
    public=forms.BooleanField(label='Öffentlicher Gegenstand',required=False)
    position=forms.IntegerField(label='Reihenfolge neuer TOP',min_value=1,required=False)
    markdown=forms.CharField(label='Unterlage zu neuem Gegenstand',max_length=100000,required=False,widget=forms.Textarea)
    item=forms.ModelChoiceField(label='Betroffener TOP',queryset=AgendaItem.objects.none(),required=False)
    template=forms.ModelChoiceField(label='Zusätzliche Vorlagenfassung',queryset=Template.objects.none(),required=False)
    starts_at=forms.DateTimeField(label='Neuer Beginn',required=False,widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    ends_at=forms.DateTimeField(label='Neues Ende',required=False,widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    expected_version=forms.IntegerField(widget=forms.HiddenInput)
    def __init__(self,*args,meeting,context,**kwargs):
        super().__init__(*args,**kwargs);self.fields['item'].queryset=AgendaItem.objects.filter(meeting=meeting,removed=False)
        self.fields['template'].queryset=Template.objects.filter(pk__in=[t.pk for t in Template.objects.filter(state='ready') if template_access(context,'read',t)])
    def clean(self):
        data=super().clean();kind=data.get('kind')
        if kind in ('urgent','correction') and not data.get('title'):self.add_error('title','Titel erforderlich.')
        if kind=='urgent' and not data.get('position'):self.add_error('position','Reihenfolge erforderlich.')
        if kind in ('correction','remove','attachment') and not data.get('item'):self.add_error('item','Betroffener TOP erforderlich.')
        if kind=='attachment' and not data.get('template'):self.add_error('template','Vorlage erforderlich.')
        if kind=='reschedule' and (not data.get('starts_at') or not data.get('ends_at') or data['ends_at']<=data['starts_at']):self.add_error('starts_at','Gültiger neuer Zeitraum erforderlich.')
        return data
    def payload(self):
        d=self.cleaned_data
        return {name:(str(value.pk) if hasattr(value,'pk') else value.isoformat() if hasattr(value,'isoformat') else value) for name,value in {'title':d.get('title'),'public_title':d.get('public_title'),'public':d.get('public'),'position':d.get('position'),'markdown':d.get('markdown'),'item_id':d.get('item'),'template_id':d.get('template'),'starts_at':d.get('starts_at'),'ends_at':d.get('ends_at')}.items()}

@login_required
@require_http_methods(['GET','POST'])
def amendment(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'plan',obj) or obj.state!='invited':raise PermissionDenied
    form=AmendmentForm(request.POST if request.method=='POST' else None,meeting=obj,context=context,initial={'expected_version':obj.version})
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                obj=lock_meeting(context,obj.pk,'plan',form.cleaned_data['expected_version'])
                change=MeetingAmendment.objects.create(meeting=obj,base_version=obj.version,kind=form.cleaned_data['kind'],reason=form.cleaned_data['reason'],data=form.payload(),requested_by=request.user)
                AuditEvent.objects.create(actor=request.user,action='meeting.amendment_requested',object_id=str(change.pk),metadata={'kind':change.kind,'reason':change.reason})
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:return redirect('meeting_detail',meeting_id=obj.pk)
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Dokumentierten Nachtrag beantragen'})

@login_required
@require_POST
def approve(request,change_id):
    change=get_object_or_404(MeetingAmendment,pk=change_id)
    try:approve_amendment(active_context(request),change_id,request.POST.get('decision_record',''))
    except ValidationError as e:messages.error(request,str(e))
    return redirect('meeting_detail',meeting_id=change.meeting_id)

@login_required
@require_POST
def guest(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'plan',obj):raise PermissionDenied
    member=get_object_or_404(Membership,pk=request.POST.get('membership'),organization=obj.organization)
    if not available_contexts(member.user).filter(pk=member.pk).exists():raise PermissionDenied
    MeetingGuest.objects.update_or_create(meeting=obj,membership=member,defaults={'expires_at':obj.ends_at+timezone.timedelta(days=1),'private':request.POST.get('private')=='on'})
    AuditEvent.objects.create(actor=request.user,action='meeting.guest',object_id=str(obj.pk),metadata={'membership':str(member.pk),'private':request.POST.get('private')=='on'})
    return redirect('meeting_detail',meeting_id=meeting_id)
