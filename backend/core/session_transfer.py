"""Allowlisted session bundles: internal polling, explicit internal acceptance."""
import hashlib,json
from django.conf import settings
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from . import models
from .meetings_service import meeting_access
from .permissions import available_contexts
from .exchange import scalar,expect_keys,upsert,authorize,transport

TABLES={
'minutes':(models.Minutes,['id','meeting_id','kind','markdown','public_markdown','state','version','published_version','public_snapshot']),
'minutes_versions':(models.MinutesVersion,['id','minutes_id','version','snapshot','reason','actor_id','correction_meeting_id']),
'decision_updates':(models.DecisionUpdate,['id','decision_id','version','snapshot','actor_id']),
'participants':(models.MeetingParticipant,['id','meeting_id','user_id','person_id','mandate_id','name','function','voting','present','substitutes_for_id']),
'events':(models.MeetingEvent,['id','meeting_id','item_id','kind','payload','digest','actor_id','context_id','device','occurred_at','version']),
'conflicts':(models.ConflictOfInterest,['id','participant_id','item_id','active','reason']),
'notes':(models.ItemNote,['item_id','markdown']),
'motions':(models.Motion,['id','item_id','applicant','wording','kind','position','state']),
'votes':(models.Vote,['id','meeting_id','item_id','wording','mode','rule','options','electorate','state','result','opened_version']),
'ballots':(models.Ballot,['id','vote_id','participant_id','choice','request_id']),
'decisions':(models.Decision,['id','vote_id','wording','result','chair_confirmation','confirmed_by_id','responsible_id','due_on','status','progress','version']),
}

def bundle(obj):
    item_ids=list(obj.items.values_list('pk',flat=True));participant_ids=list(obj.roster.values_list('pk',flat=True));vote_ids=list(obj.votes.values_list('pk',flat=True))
    filters={'minutes':{'meeting':obj},'minutes_versions':{'minutes__meeting':obj},'decision_updates':{'decision__vote__meeting':obj},'participants':{'meeting':obj},'events':{'meeting':obj},'conflicts':{'item_id__in':item_ids},'notes':{'item_id__in':item_ids},'motions':{'item_id__in':item_ids},'votes':{'meeting':obj},'ballots':{'vote_id__in':vote_ids},'decisions':{'vote_id__in':vote_ids}}
    return {'meeting_id':str(obj.pk),'version':obj.version,'state':obj.state,'active_item_id':str(obj.active_item_id) if obj.active_item_id else None,'paused':obj.paused, 'tables':{key:[scalar(r,fields) for r in model.objects.filter(**filters[key])] for key,(model,fields) in TABLES.items()}}


def validate(data,obj,check_actors=False):
    expect_keys(data,['meeting_id','version','state','active_item_id','paused','tables']);expect_keys(data['tables'],list(TABLES))
    if data['meeting_id']!=str(obj.pk) or type(data['version'])!=int or data['version']<obj.authority_base or type(data['paused'])!=bool:raise ValidationError('Ungültiger Sitzungsstand.')
    items={str(pk) for pk in obj.items.values_list('pk',flat=True)}
    if data['active_item_id'] and data['active_item_id'] not in items:raise ValidationError('Fremder aktiver TOP.')
    ids={key:{str(row.get('id',row.get('item_id'))) for row in rows} for key,rows in data['tables'].items()}
    total=sum(len(rows) for rows in data['tables'].values())
    if total>20000:raise ValidationError('Sitzungsjournal zu groß.')
    for key,rows in data['tables'].items():
        model,fields=TABLES[key]
        for row in rows:
            expect_keys(row,fields)
            if row.get('meeting_id',str(obj.pk))!=str(obj.pk) or row.get('item_id') and row['item_id'] not in items:raise ValidationError('Fremdes Sitzungsobjekt.')
            if row.get('minutes_id') and row['minutes_id'] not in ids['minutes'] or row.get('decision_id') and row['decision_id'] not in ids['decisions']:raise ValidationError('Fremde Niederschrifts-/Beschlussreferenz.')
            if row.get('correction_meeting_id') and not models.Meeting.objects.filter(pk=row['correction_meeting_id'],committee=obj.committee,starts_at__gt=obj.starts_at).exists():raise ValidationError('Fremde Folgesitzung.')
            if row.get('participant_id') and row['participant_id'] not in ids['participants'] or row.get('vote_id') and row['vote_id'] not in ids['votes'] or row.get('substitutes_for_id') and row['substitutes_for_id'] not in ids['participants']:raise ValidationError('Fremde Sitzungsreferenz.')
            if key=='participants':
                if row['mandate_id'] and not models.Mandate.objects.filter(pk=row['mandate_id'],committee=obj.committee,user_id=row['user_id'],person_id=row['person_id']).exists():raise ValidationError('Fremdes Mandat.')
                if row['user_id'] and not models.User.objects.filter(pk=row['user_id']).exists():raise ValidationError('Unbekannte Person.')
            if key=='events':
                from .live_service import digest
                if row['digest']!=digest(row['kind'],row['payload']) or row['version']>data['version']:raise ValidationError('Ungültiges Ereignis.')
                if check_actors:
                    c=models.Membership.objects.filter(pk=row['context_id'],user_id=row['actor_id'],organization=obj.organization).first()
                    if not c or not meeting_access(c,'live',obj) or c.user_id not in (obj.scribe_id,obj.chair_id):raise ValidationError('Ereignisakteur besitzt keine aktuelle Sitzungserlaubnis.')
            if key=='ballots' and not any(v['id']==row['vote_id'] and v['mode']=='named' and row['participant_id'] in v['electorate'] and row['choice'] in v['options'] for v in data['tables']['votes']):raise ValidationError('Ungültige Stimmzuordnung.')
            # A UUID cannot be used to overwrite a row belonging to another session.
            pk=row.get('id',row.get('item_id'));old=model.objects.filter(pk=pk).first()
            if old:
                if key in ('participants','events','votes','minutes'):foreign=old.meeting_id!=obj.pk
                elif key in ('notes','motions','conflicts'):foreign=old.item.meeting_id!=obj.pk
                elif key=='minutes_versions':foreign=old.minutes.meeting_id!=obj.pk
                elif key=='decision_updates':foreign=old.decision.vote.meeting_id!=obj.pk
                else:foreign=old.vote.meeting_id!=obj.pk
                if foreign:raise ValidationError('Datensatz gehört zu einer anderen Sitzung.')


def apply(data,obj):
    validate(data,obj)
    for key in ['participants','events','conflicts','notes','motions','votes','ballots','decisions','minutes','minutes_versions','decision_updates']:
        model,fields=TABLES[key]
        rows=data['tables'][key]
        if key=='participants':
            rows=sorted(rows,key=lambda r:bool(r['substitutes_for_id']))
        for row in rows:
            if key in ('events','ballots','minutes_versions','decision_updates'):
                old=model.objects.filter(pk=row['id']).first()
                if old:
                    if scalar(old,fields)!=row:raise ValidationError('Unveränderlicher Stand widerspricht dem Journal.')
                    continue
            if key=='notes':model.objects.update_or_create(item_id=row['item_id'],defaults={'markdown':row['markdown']})
            else:upsert(model,[row],fields)
    obj.active_item_id=data['active_item_id'];obj.paused=data['paused'];obj.state=data['state'];obj.version=data['version'];obj.save()

@transaction.atomic
def prepare_return(context,obj,version):
    obj=models.Meeting.objects.select_for_update().get(pk=obj.pk)
    if settings.SERVER_ROLE!='protected' or obj.leading_server!='protected' or not meeting_access(context,'protocol',obj) or context.user_id not in (obj.scribe_id,obj.chair_id):raise PermissionDenied
    if obj.version!=version or obj.state not in ('finished','protocol_review','approved'):raise ValidationError('Sitzung zuerst abschließen; aktuellen Stand prüfen.')
    data=bundle(obj);validate(data,obj)
    obj.state='return_pending';obj.version+=1;obj.save(update_fields=['state','version'])
    return models.SessionReturn.objects.create(meeting=obj,base_version=obj.authority_base,bundle=data,digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),requested_by=context.user,context_id=context.pk)

@transaction.atomic
def accept(context,return_id,reason):
    change=models.SessionReturn.objects.select_for_update().select_related('meeting').get(pk=return_id)
    obj=models.Meeting.objects.select_for_update().get(pk=change.meeting_id)
    if settings.SERVER_ROLE!='internal' or not meeting_access(context,'protocol',obj):raise PermissionDenied
    if change.state!='pending' or obj.leading_server!='protected' or obj.version!=change.base_version or not reason.strip():raise ValidationError('Rückgabe, Führerschaft oder Basisstand geändert; ausdrücklich prüfen.')
    c=models.Membership.objects.filter(pk=change.context_id,user=change.requested_by).first()
    if not c or not meeting_access(c,'protocol',obj):raise PermissionDenied
    if change.digest!=hashlib.sha256(json.dumps(change.bundle,sort_keys=True).encode()).hexdigest():raise ValidationError('Rückgabe verändert.')
    validate(change.bundle,obj,True);apply(change.bundle,obj)
    obj.leading_server='internal';obj.version+=2;obj.save(update_fields=['leading_server','version'])
    change.state='accepted';change.reviewed_by=context.user;change.reason=reason[:1000];change.save()
    models.AuditEvent.objects.create(actor=context.user,action='session.return.accepted',object_id=str(change.pk),metadata={'reason':reason,'version':obj.version})
    return obj

@csrf_exempt
@require_GET
def returns_endpoint(request):
    if settings.SERVER_ROLE!='protected':raise PermissionDenied
    authorize(request,'protected')
    return JsonResponse({'returns':[scalar(r,['id','meeting_id','base_version','bundle','digest','requested_by_id','context_id']) for r in models.SessionReturn.objects.filter(state='pending')[:20]]})

def pull_returns():
    data=transport('protected','/transfer/sessions/');expect_keys(data,['returns'])
    for row in data['returns']:
        expect_keys(row,['id','meeting_id','base_version','bundle','digest','requested_by_id','context_id'])
        obj=models.Meeting.objects.get(pk=row['meeting_id']);validate(row['bundle'],obj)
        if obj.leading_server!='protected' or obj.authority_base!=row['base_version']:raise ValidationError('Keine passende externe Führerschaft.')
        models.SessionReturn.objects.get_or_create(pk=row['id'],defaults={k:v for k,v in row.items() if k!='id'})
