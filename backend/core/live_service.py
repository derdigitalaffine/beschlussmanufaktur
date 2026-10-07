import hashlib,json,uuid
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Meeting,MeetingParticipant,MeetingLease,MeetingEvent,Membership,Mandate,ConflictOfInterest,ItemNote,AgendaItem,Motion,AuditEvent,ExchangePolicy
from .meetings_service import meeting_access,lock_meeting
from .permissions import available_contexts


def digest(kind,payload):
    stable={k:v for k,v in payload.items() if not (kind=='quorum' and k=='calculation')}
    return hashlib.sha256(json.dumps({'kind':kind,'payload':stable},sort_keys=True).encode()).hexdigest()

def event(obj,context,device,kind,payload,event_id=None,occurred_at=None):
    return MeetingEvent.objects.create(id=event_id or uuid.uuid4(),meeting=obj,item_id=payload.get('item_id') or obj.active_item_id,kind=kind,payload=payload,digest=digest(kind,payload),actor=context.user,context_id=context.pk,device=device,occurred_at=occurred_at or timezone.now(),version=obj.version)


def voter_groups(obj,item=None):
    people=list(obj.roster.filter(present=True,voting=True).select_related('substitutes_for'))
    blocked=set(ConflictOfInterest.objects.filter(item=item,active=True).values_list('participant_id',flat=True)) if item else set()
    # A primary seat takes precedence while its principal is present. Multiple
    # replacements never silently acquire two votes for the same seat.
    present_ids={p.pk for p in people if p.pk not in blocked}
    groups={}
    for p in people:
        if p.pk in blocked or p.substitutes_for_id and p.substitutes_for_id in present_ids:continue
        seat=p.substitutes_for_id or p.pk;groups.setdefault(seat,[]).append(p)
    return groups


def effective_voters(obj,item=None):return [group[0] for group in voter_groups(obj,item).values() if len(group)==1]


def ambiguous_voters(obj,item=None):return [p.name for group in voter_groups(obj,item).values() if len(group)>1 for p in group]


def quorum(obj,item=None):
    count=len(effective_voters(obj,item));rules=obj.rules or {}
    ambiguous=ambiguous_voters(obj,item)
    if ambiguous:return {'present':count,'required':None,'calculated':None,'rule':'vertretung_unklar','ambiguous':ambiguous}
    method=rules.get('quorum','majority_statutory')
    if method=='repeated_minimum':required=int(rules.get('minimum',3))
    elif method=='majority_nonexcluded':
        excluded=ConflictOfInterest.objects.filter(item=item,active=True,participant__voting=True).count() if item else 0
        required=max(1,(obj.statutory_count-excluded)//2+1)
    elif method=='manual':return {'present':count,'required':None,'calculated':None,'rule':method}
    else:required=obj.statutory_count//2+1
    return {'present':count,'required':required,'calculated':count>=required,'rule':method}


@transaction.atomic
def activate(context,meeting_id,version,server,rules):
    obj=lock_meeting(context,meeting_id,'invite',version)
    if obj.state!='invited' or obj.leading_server!='internal':raise ValidationError('Nur intern eingeladene Sitzungen aktivieren.')
    if not available_contexts(obj.scribe).filter(organization=obj.organization,role='clerk').exists() or not available_contexts(obj.chair).filter(organization=obj.organization,role__in=['chair','mayor','local_mayor']).exists():raise ValidationError('Schriftführung und Vorsitz benötigen gültige ausdrückliche Fachrollen in dieser Körperschaft.')
    if server not in ('internal','protected'):raise ValidationError('Unbekannter führender Dienst.')
    if rules.get('quorum') not in ('majority_statutory','majority_nonexcluded','repeated_minimum','manual'):raise ValidationError('Beschlussfähigkeitsregel fehlt.')
    if server=='protected' and (not ExchangePolicy.objects.filter(organization=obj.organization,protected_enabled=True).exists() or not settings.EXCHANGE_PROTECTED_URL or len(settings.EXCHANGE_PROTECTED_KEY)<32):raise ValidationError('Geschützte Bereitstellung und Transferkonfiguration erforderlich.')
    obj.leading_server=server;obj.rules=rules;obj.version+=1;obj.authority_base=obj.version;obj.save()
    AuditEvent.objects.create(actor=context.user,action='meeting.activated',object_id=str(obj.pk),metadata={'server':server,'rules':rules,'version':obj.version})
    return obj


@transaction.atomic
def claim(context,meeting_id,version,device,reason=''):
    obj=lock_meeting(context,meeting_id,'live',version)
    if context.user_id not in (obj.scribe_id,obj.chair_id):raise PermissionDenied('Nur zugeordnete Schriftführung oder Vorsitz übernimmt.')
    if obj.state not in ('invited','live'):raise ValidationError('Sitzung ist nicht zur Livebearbeitung geöffnet.')
    lease=MeetingLease.objects.select_for_update().filter(meeting=obj).first()
    now=timezone.now()
    if lease and (lease.holder_id!=context.user_id or lease.device!=device) and lease.expires_at>now:
        if context.user_id!=obj.chair_id or not reason.strip():raise ValidationError('Eine andere Schriftführung ist aktiv. Vorsitz kann mit Begründung übernehmen.')
    epoch=(lease.epoch+1) if lease else 1
    MeetingLease.objects.update_or_create(meeting=obj,defaults={'holder':context.user,'context_id':context.pk,'device':device,'epoch':epoch,'expires_at':now+timezone.timedelta(seconds=180)})
    obj.version+=1;obj.save(update_fields=['version'])
    event(obj,context,device,'takeover',{'reason':reason or 'Schriftführung übernommen','epoch':epoch})
    return epoch


def assert_writer(obj,context,device,epoch):
    if not meeting_access(context,'live',obj) or obj.leading_server!=settings.SERVER_ROLE:raise PermissionDenied
    lease=MeetingLease.objects.select_for_update().filter(meeting=obj,holder=context.user,context_id=context.pk,device=device,epoch=epoch,expires_at__gt=timezone.now()).first()
    if not lease:raise ValidationError('Sitzungshoheit ist abgelaufen oder übernommen. Bitte den aktuellen Stand laden und ausdrücklich übernehmen.')
    lease.expires_at=timezone.now()+timezone.timedelta(seconds=180);lease.save(update_fields=['expires_at'])
    return lease


@transaction.atomic
def renew(context,meeting_id,device,epoch):
    obj=Meeting.objects.select_for_update().get(pk=meeting_id);assert_writer(obj,context,device,epoch);return obj.version


@transaction.atomic
def roster(context,meeting_id,version,device,epoch):
    obj=lock_meeting(context,meeting_id,'live',version);assert_writer(obj,context,device,epoch)
    if obj.state not in ('invited','live'):raise ValidationError('Keine aktive Sitzung.')
    day=timezone.localtime(obj.starts_at).date()
    mandates=list(Mandate.objects.filter(committee=obj.committee,archived=False,starts_on__lte=day,ends_on__gte=day).select_related('user','person','function'))
    mapping={}
    for mandate in mandates:
        person=mandate.user or mandate.person
        name=(person.get_full_name() or person.email) if mandate.user_id else person.name
        lookup={'user':mandate.user} if mandate.user_id else {'person':mandate.person}
        part,_=MeetingParticipant.objects.get_or_create(meeting=obj,**lookup,defaults={'name':name,'function':mandate.function.name,'mandate':mandate,'voting':mandate.voting})
        mapping[mandate.pk]=part
    for mandate in mandates:
        if mandate.substitutes_for_id and mandate.substitutes_for_id in mapping:
            part=mapping[mandate.pk];part.substitutes_for=mapping[mandate.substitutes_for_id];part.save(update_fields=['substitutes_for'])
    from .models import Vote
    Vote.objects.filter(meeting=obj,state='open').update(state='aborted')
    obj.version+=1;obj.save(update_fields=['version']);event(obj,context,device,'roster',{'count':len(mapping)})
    return obj


def apply_payload(obj,kind,data):
    if kind in ('eligibility','conflict','quorum') and (not isinstance(data.get('reason'),str) or not data['reason'].strip() or len(data['reason'])>1000):raise ValidationError('Feststellungsgrund muss ein Text mit höchstens 1000 Zeichen sein.')
    if kind=='begin':
        if obj.state!='invited':raise ValidationError('Sitzung kann nur einmal begonnen werden.')
        obj.state='live'
    elif kind=='end':
        if obj.state!='live':raise ValidationError('Keine laufende Sitzung.')
        obj.state='finished';obj.paused=False
    elif kind in ('pause','resume'):
        if obj.state!='live':raise ValidationError('Keine laufende Sitzung.')
        obj.paused=kind=='pause'
    elif kind=='top':
        if obj.state!='live':raise ValidationError('Keine laufende Sitzung.')
        item=AgendaItem.objects.get(pk=data['item_id'],meeting=obj,removed=False);obj.active_item=item
    elif kind=='presence':
        if obj.state not in ('invited','live'):raise ValidationError('Anwesenheit ist nur vor oder während der Sitzung erfassbar.')
        if not isinstance(data['present'],bool):raise ValidationError('Anwesenheitswert muss wahr/falsch sein.')
        person=MeetingParticipant.objects.get(pk=data['participant_id'],meeting=obj);person.present=data['present'];person.save(update_fields=['present'])
    elif kind=='eligibility':
        if not isinstance(data.get('voting'),bool) or not data.get('reason','').strip():raise ValidationError('Stimmrechtsfeststellung und Begründung erforderlich.')
        person=MeetingParticipant.objects.get(pk=data['participant_id'],meeting=obj);person.voting=data['voting'];person.save(update_fields=['voting'])
    elif kind=='conflict':
        person=MeetingParticipant.objects.get(pk=data['participant_id'],meeting=obj)
        item=AgendaItem.objects.get(pk=data['item_id'],meeting=obj)
        if not isinstance(data['active'],bool) or not data.get('reason','').strip():raise ValidationError('Feststellung/Begründung und aktiver Status erforderlich.')
        ConflictOfInterest.objects.update_or_create(participant=person,item=item,defaults={'active':data['active'],'reason':data['reason'][:1000]})
    elif kind=='text':
        item=AgendaItem.objects.get(pk=data['item_id'],meeting=obj)
        if not isinstance(data['markdown'],str) or len(data['markdown'])>100000:raise ValidationError('Text ist zu groß.')
        ItemNote.objects.update_or_create(item=item,defaults={'markdown':data['markdown']})
    elif kind=='motion':
        item=AgendaItem.objects.get(pk=data['item_id'],meeting=obj)
        if data.get('kind') not in ('substantive','amendment','procedure') or not data.get('wording','').strip() or len(data['wording'])>100000:raise ValidationError('Ungültiger Antrag.')
        if not 1<=int(data.get('position',1))<=1000:raise ValidationError('Ungültige Antragsreihenfolge.')
        Motion.objects.create(item=item,applicant=data['applicant'][:200],wording=data['wording'],kind=data['kind'],position=int(data.get('position',1)))
    elif kind=='quorum':
        item=AgendaItem.objects.get(pk=data['item_id'],meeting=obj)
        if not isinstance(data['confirmed'],bool) or not data.get('reason','').strip():raise ValidationError('Ausdrückliche Feststellung und Begründung erforderlich.')
        data['calculation']=quorum(obj,item)
    else:raise ValidationError('Unbekanntes Sitzungsereignis.')
    # Any roster change invalidates an open ballot; implemented by the voting module.
    if kind in ('presence','eligibility','conflict','end','pause','top','roster'):
        from django.apps import apps
        try:vote_model=apps.get_model('core','Vote')
        except LookupError:vote_model=None
        if vote_model:vote_model.objects.filter(meeting=obj,state='open').update(state='aborted')


@transaction.atomic
def write(context,meeting_id,version,device,epoch,kind,data,event_id,occurred_at=None):
    obj=Meeting.objects.select_for_update().get(pk=meeting_id)
    assert_writer(obj,context,device,epoch)
    if not isinstance(data,dict):raise ValidationError('Sitzungsereignis benötigt ein Objekt.')
    if data.get('item_id') and not AgendaItem.objects.filter(pk=data['item_id'],meeting=obj).exists():raise ValidationError('TOP gehört nicht zu dieser Sitzung.')
    existing=MeetingEvent.objects.filter(pk=event_id).first()
    if existing:
        if existing.meeting_id!=obj.pk or existing.actor_id!=context.user_id or existing.digest!=digest(kind,data):raise ValidationError('Ereignis-ID wurde bereits anders verwendet.')
        return existing
    if obj.version!=version:raise ValidationError('Sitzungsstand wurde geändert. Lokale Daten nicht überschrieben; bitte prüfen und erneut erfassen.')
    if obj.state not in ('invited','live'):raise ValidationError('Sitzung ist nicht mehr bearbeitbar.')
    timestamp=parse_datetime(occurred_at) if occurred_at else timezone.now()
    if not timestamp or timezone.is_naive(timestamp) or timestamp>timezone.now()+timezone.timedelta(minutes=5):raise ValidationError('Ungültiger fachlicher Zeitpunkt.')
    apply_payload(obj,kind,data);obj.version+=1;obj.save()
    result=event(obj,context,device,kind,data,event_id,timestamp)
    AuditEvent.objects.create(actor=context.user,action='meeting.event',object_id=str(result.pk),metadata={'meeting':str(obj.pk),'version':obj.version,'kind':kind})
    return result
