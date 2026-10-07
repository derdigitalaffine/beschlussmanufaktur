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
    for person in people:person.conflicted=perso…7954 tokens truncated…raise ValidationError('Archivierte Fassungen sind unveränderlich.')
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError('Archivierte Fassungen bleiben erhalten.')


class TemplateParticipant(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='participants')
    membership = models.ForeignKey(Membership,on_delete=models.PROTECT)
    actions = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True,blank=True)
    revoked_at = models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['template','membership'],name='unique_template_participant')]


class Consultation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='consultations')
    committee = models.ForeignKey(RegistryRecord,on_delete=models.PROTECT)
    position = models.PositiveIntegerField(default=1)
    deciding = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    may_amend = models.BooleanField(default=False)
    amendment = models.TextField(blank=True,max_length=100000)
    version = models.PositiveIntegerField(default=1)
    class Meta:ordering=['position','id']


class TemplateLink(models.Model):
    source = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='links')
    target = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='backlinks')
    description = models.CharField(max_length=200)


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='attachments')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='attachments/%Y/%m')
    digest = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    media_type = models.CharField(max_length=100)
    public = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    removed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TemplateComment(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='comments')
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    text = models.TextField(max_length=4000)
    version = models.PositiveIntegerField()
    task_assignee = models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT,related_name='template_tasks')
    completed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    path = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True)
    emailed_at = models.DateTimeField(null=True)


class EditPresence(models.Model):
    template = models.ForeignKey(Template,on_delete=models.CASCADE)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    seen_at = models.DateTimeField(default=timezone.now)
    class Meta:constraints=[models.UniqueConstraint(fields=['template','user'],name='unique_edit_presence')]


class ReviewStep(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='review_steps')
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=30)
    substitute = models.CharField(max_length=30,blank=True)
    group = models.PositiveIntegerField()
    assigned = models.ForeignKey(Membership,null=True,blank=True,on_delete=models.PROTECT)
    state = models.CharField(max_length=20,default='pending')
    decided_by = models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    decided_at = models.DateTimeField(null=True)
    comment = models.CharField(max_length=1000,blank=True)


class NumberSequence(models.Model):
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    year = models.PositiveIntegerField()
    value = models.PositiveIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=['organization','year'],name='unique_number_sequence')]


class Publication(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    subject = models.CharField(max_length=300)
    markdown = models.TextField(max_length=100000)
    approved_by = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True)


class ExternalDocument(models.Model):
    id = models.UUIDField(primary_key=True)
    organization_id = models.UUIDField()
    title = models.CharField(max_length=300)
    markdown = models.TextField()
    number = models.CharField(max_length=40,blank=True)
    version = models.PositiveIntegerField()
    permissions = models.JSONField(default=dict)
    attachments = models.JSONField(default=list)
    received_at = models.DateTimeField(default=timezone.now)


class ReplicaAsset(models.Model):
    id = models.UUIDField(primary_key=True)
    digest = models.CharField(max_length=64)
    data = models.BinaryField()
    received_at = models.DateTimeField(auto_now=True)


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    committee = models.ForeignKey(RegistryRecord,on_delete=models.PROTECT,related_name='meetings')
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    room = models.ForeignKey(RegistryRecord,null=True,blank=True,on_delete=models.PROTECT,related_name='room_meetings')
    location = models.CharField(max_length=300)
    chair = models.ForeignKey(User,on_delete=models.PROTECT,related_name='chaired_meetings')
    scribe = models.ForeignKey(User,on_delete=models.PROTECT,related_name='scribed_meetings')
    created_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='created_meetings')
    paused = models.BooleanField(default=False)
    state = models.CharField(max_length=30,default='preparation')
    version = models.PositiveIntegerField(default=1)
    rules = models.JSONField(default=dict,blank=True)
    statutory_count = models.PositiveIntegerField(default=1)
    invitation_days = models.PositiveIntegerField(default=4)
    proposal_deadline = models.DateTimeField(null=True,blank=True)
    release_deadline = models.DateTimeField(null=True,blank=True)
    public_notice = models.TextField(blank=True,max_length=10000)
    public_enabled = models.BooleanField(default=False)
    permission_snapshot = models.JSONField(default=dict,blank=True)
    leading_server = models.CharField(max_length=20,default='internal')
    active_item = models.ForeignKey('AgendaItem',null=True,blank=True,on_delete=models.PROTECT,related_name='+')
    class Meta:ordering=['starts_at','id']
    def clean(self):
        if self.committee_id and (self.committee.kind!='committee' or self.committee.organization_id!=self.organization_id):raise ValidationError('Gremium gehört nicht zur Körperschaft.')
        if self.room and (self.room.kind!='room' or self.room.organization_id!=self.organization_id):raise ValidationError('Raum gehört nicht zur Körperschaft.')
        if self.ends_at and self.starts_at and self.ends_at<=self.starts_at:raise ValidationError('Sitzungsende muss nach Beginn liegen.')
        if self.statutory_count<1:raise ValidationError('Gesetzliche Mitgliederzahl erforderlich.')
        for person_id in (self.chair_id,self.scribe_id):
            if person_id and not Membership.objects.filter(user_id=person_id,organization=self.organization).exists():raise ValidationError('Vorsitz und Schriftführung brauchen einen zugehörigen Arbeitskontext.')


class AgendaItem(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='items')
    parent = models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='subitems')
    position = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=300)
    public_title = models.CharField(max_length=300,blank=True)
    public = models.BooleanField(default=True)
    template = models.ForeignKey(Template,null=True,blank=True,on_delete=models.PROTECT)
    markdown = models.TextField(blank=True,max_length=100000)
    frozen_template = models.JSONField(default=dict,blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True,blank=True)
    proposed_by = models.ForeignKey(User,on_delete=models.PROTECT)
    removed = models.BooleanField(default=False)
    class Meta:ordering=['position','id']
    def clean(self):
        parent=self.parent;seen={self.pk}
        while parent:
            if parent.pk in seen or parent.meeting_id!=self.meeting_id:raise ValidationError('Ungültige TOP-Untergliederung.')
            seen.add(parent.pk);parent=parent.parent
        if self.position<1:raise ValidationError('Reihenfolge beginnt bei 1.')
        if not self.public and not self.public_title.strip():raise ValidationError('Nichtöffentlicher TOP benötigt einen unverfänglichen Bekanntmachungstitel.')


class MeetingInvitation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='invitations')
    revision = models.PositiveIntegerField()
    snapshot = models.JSONField()
    digest = models.CharField(max_length=64)
    reason = models.CharField(max_length=1000,blank=True)
    issued_by = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['meeting','revision'],name='unique_meeting_invitation')]
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Versandstände sind unveränderlich.')
        super().save(*args,**kwargs)


class InvitationDelivery(models.Model):
    invitation = models.ForeignKey(MeetingInvitation,on_delete=models.PROTECT,related_name='deliveries')
    user = models.ForeignKey(User,on_delete=models.PROTECT)
    snapshot = models.JSONField()
    delivered_at = models.DateTimeField(null=True,blank=True)
    seen_at = models.DateTimeField(null=True,blank=True)
    error = models.CharField(max_length=200,blank=True)
    attempts = models.PositiveIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=['invitation','user'],name='unique_invitation_delivery')]


class MeetingGuest(models.Model):
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    membership = models.ForeignKey(Membership,on_delete=models.PROTECT)
    expires_at = models.DateTimeField()
    private = models.BooleanField(default=False)
    class Meta:constraints=[models.UniqueConstraint(fields=['meeting','membership'],name='unique_meeting_guest')]


class MeetingAmendment(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    base_version = models.PositiveIntegerField()
    kind = models.CharField(max_length=30,choices=[('correction','Berichtigung'),('urgent','Dringlicher neuer Gegenstand'),('attachment','Zusätzliche Unterlage'),('remove','Gegenstand absetzen'),('reschedule','Termin ändern')])
    reason = models.CharField(max_length=1000)
    data = models.JSONField()
    requested_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='meeting_amendments')
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    state = models.CharField(max_length=20,default='pending')
    decision_record = models.CharField(max_length=1000,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MeetingParticipant(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='roster')
    user = models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT)
    person = models.ForeignKey(RegistryRecord,null=True,blank=True,on_delete=models.PROTECT)
    mandate = models.ForeignKey(Mandate,null=True,blank=True,on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    function = models.CharField(max_length=200,blank=True)
    voting = models.BooleanField(default=False)
    present = models.BooleanField(default=False)
    substitutes_for = models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['meeting','user'],name='unique_meeting_user'),models.UniqueConstraint(fields=['meeting','person'],name='unique_meeting_person')]


class MeetingLease(models.Model):
    meeting = models.OneToOneField(Meeting,on_delete=models.PROTECT,primary_key=True)
    holder = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    device = models.UUIDField()
    epoch = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField()


class MeetingEvent(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='events')
    item = models.ForeignKey(AgendaItem,null=True,blank=True,on_delete=models.PROTECT)
    kind = models.CharField(max_length=30)
    payload = models.JSONField(default=dict,blank=True)
    digest = models.CharField(max_length=64)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    device = models.UUIDField()
    occurred_at = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    class Meta:ordering=['version','id']
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Ereignisse sind unveränderlich; Korrektur als neues Ereignis erfassen.')
        super().save(*args,**kwargs)


class ConflictOfInterest(models.Model):
    participant = models.ForeignKey(MeetingParticipant,on_delete=models.PROTECT)
    item = models.ForeignKey(AgendaItem,on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    reason = models.CharField(max_length=1000)
    class Meta:constraints=[models.UniqueConstraint(fields=['participant','item'],name='unique_item_conflict')]


class ItemNote(models.Model):
    item = models.OneToOneField(AgendaItem,on_delete=models.PROTECT,primary_key=True)
    markdown = models.TextField(max_length=100000,blank=True)


class Motion(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    item = models.ForeignKey(AgendaItem,on_delete=models.PROTECT,related_name='motions')
    applicant = models.CharField(max_length=200)
    wording = models.TextField(max_length=100000)
    kind = models.CharField(max_length=30,choices=[('substantive','Sachantrag'),('amendment','Änderungsantrag'),('procedure','Geschäftsordnungsantrag')])
    position = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=30,default='pending')
