"""Explicit preparation and atomic reconciliation; no offline votes or approvals."""
import uuid,json,hashlib,copy
from django.conf import settings
from django.core import signing
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET,require_POST
from .models import Meeting,MeetingLease,MeetingEvent,PersonalNote,OfflineReceipt,AuditEvent,ItemNote
from .permissions import active_context
from .meetings_service import meeting_access,meeting_snapshot
from .live_views import device
from .live_service import claim,write
from .member_views import save_note

GRANT_FIELDS=('meeting_id','user_id','context_id','version','epoch','device','expires_at')

def permit(data):return signing.dumps({field:data[field] for field in GRANT_FIELDS},salt='offline-session-v1')

ALLOWED={'begin','end','pause','resume','top','presence','conflict','text','motion','quorum'}

@login_required
@require_GET
def identity(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    return JsonResponse({'user_id':str(request.user.pk),'context_id':str(context.pk),'label':context.organization.name+' · '+context.get_role_display(),'email':request.user.email,'csrf':get_token(request),'server':settings.SERVER_ROLE})

@login_required
@require_POST
def prepare(request,meeting_id):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    try:hours=int(request.POST.get('hours',48))
    except ValueError:return JsonResponse({'error':'Ungültige Offline-Dauer.'},status=400)
    if not 1<=hours<=168 or not obj.rules.get('offline_enabled',True):return JsonResponse({'error':'Offline-Vorbereitung ist deaktiviert oder Dauer ungültig.'},status=400)
    expires=timezone.now()+timezone.timedelta(hours=hours)
    if context.ends_at:expires=min(expires,context.ends_at)
    lease=MeetingLease.objects.filter(meeting=obj,holder=request.user,context_id=context.pk,device=device(request),expires_at__gt=timezone.now()).first()
    writer=bool(lease and meeting_access(context,'live',obj) and obj.leading_server==settings.SERVER_ROLE and obj.state in ('invited','live'))
    note=PersonalNote.objects.filter(owner=request.user,context=context,meeting=obj).first()
    data={'schema':1,'user_id':str(request.user.pk),'context_id':str(context.pk),'label':context.organization.name+' · '+context.get_role_display(),'meeting_id':str(obj.pk),'expires_at':expires.isoformat(),'prepared_at':timezone.now().isoformat(),'version':obj.version,'epoch':lease.epoch if writer else None,'device':str(device(request)),'writer':writer,'meeting':meeting_snapshot(obj,context),'roster':list(obj.roster.values('id','name','present','voting')) if writer else [],'notes':{str(n.item_id):n.markdown for n in ItemNote.objects.filter(item__meeting=obj)} if writer else {},'personal_note':{'markdown':note.markdown if note else '', 'version':note.version if note else 0},'queue':[]}
    data['grant']=permit(data)
    delivery=obj.invitations.order_by('-revision').first()
    data['packet_url']=f'/einladungen/{delivery.pk}/pdf/' if delivery and delivery.deliveries.filter(user=request.user,snapshot__context_id=str(context.pk)).exists() else None
    AuditEvent.objects.create(actor=request.user,action='offline.prepared',object_id=str(obj.pk),metadata={'context':str(context.pk),'expires_at':expires.isoformat(),'writer':writer})
    return JsonResponse(data,encoder=__import__('django.core.serializers.json',fromlist=['DjangoJSONEncoder']).DjangoJSONEncoder)

@transaction.atomic
def reconcile(context,data):
    if not isinstance(data,dict) or set(data)!={'batch_id','meeting_id','user_id','context_id','base_version','epoch','device','expires_at','events','grant'}:raise ValidationError('Unbekannter Offline-Vertrag.')
    obj=Meeting.objects.select_for_update().get(pk=data['meeting_id'])
    if not meeting_access(context,'live',obj) or context.user_id not in (obj.scribe_id,obj.chair_id) or str(context.user_id)!=data['user_id'] or str(context.pk)!=data['context_id']:raise PermissionDenied
    if obj.leading_server!=settings.SERVER_ROLE or not obj.rules.get('offline_enabled',True):raise ValidationError('Führender Dienst oder Offline-Freigabe geändert.')
    batch_id=uuid.UUID(data['batch_id']);digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    existing=OfflineReceipt.objects.filter(pk=batch_id).first()
    if existing:
        if existing.owner_id!=context.user_id or existing.context_id!=context.pk or existing.meeting_id!=obj.pk or existing.digest!=digest:raise ValidationError('Offline-ID wurde anders verwendet.')
        return existing.resulting_version
    try:grant=signing.loads(data['grant'],salt='offline-session-v1',max_age=7*86400)
    except signing.BadSignature:raise ValidationError('Offline-Freigabe ungültig oder abgelaufen.')
    expected={field:data['base_version'] if field=='version' else data[field] for field in GRANT_FIELDS}
    if grant!=expected:raise ValidationError('Offline-Freigabe gehört zu einem anderen vorbereiteten Stand.')
    expires=parse_datetime(data['expires_at'])
    if not expires or timezone.is_naive(expires) or expires<timezone.now() or expires>timezone.now()+timezone.timedelta(days=7):raise ValidationError('Lokale Freigabe abgelaufen; Texte exportieren und nach erneuter Prüfung manuell übernehmen.')
    if type(data['base_version'])!=int or obj.version!=data['base_version'] or obj.state not in ('invited','live'):raise ValidationError('Zentralstand geändert oder Sitzung geschlossen. Kein automatisches Überschreiben; lokalen Verlauf vergleichen.')
    lease=MeetingLease.objects.select_for_update().filter(meeting=obj).first();client=uuid.UUID(data['device'])
    if not lease or lease.holder_id!=context.user_id or lease.context_id!=context.pk or lease.device!=client or lease.epoch!=data['epoch']:raise ValidationError('Sitzung wurde übernommen. Offline-Verlauf muss durch die neue Schriftführung fachlich geprüft werden.')
    rows=data['events']
    if not isinstance(rows,list) or not 1<=len(rows)<=500:raise ValidationError('Ein bis 500 Ereignisse je Abgleich erforderlich.')
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','kind','payload','occurred_at'} or row['kind'] not in ALLOWED:raise ValidationError('Nur Sitzungsereignisse sind offline zulässig; keine Abstimmungen oder Freigaben.')
        if MeetingEvent.objects.filter(pk=row['id']).exists():raise ValidationError('Ereignis wurde bereits außerhalb dieses Abgleichs übernommen.')
    # A lease may have expired during disconnection. Reacquisition is explicit,
    # only for exactly the unchanged version and epoch, and inside this transaction.
    epoch=claim(context,obj.pk,obj.version,client,'Offline-Abgleich ausdrücklich übernommen')
    obj.refresh_from_db()
    for row in rows:
        write(context,obj.pk,obj.version,client,epoch,row['kind'],copy.deepcopy(row['payload']),uuid.UUID(row['id']),row['occurred_at']);obj.refresh_from_db()
    OfflineReceipt.objects.create(id=batch_id,meeting=obj,owner=context.user,context_id=context.pk,digest=digest,resulting_version=obj.version)
    return obj.version

@login_required
@require_POST
def sync(request):
    try:
        if len(request.body)>2*1024*1024:raise ValidationError('Offline-Verlauf zu groß.')
        data=json.loads(request.body);version=reconcile(active_context(request),data)
    except (ValidationError,ValueError,KeyError,TypeError,ObjectDoesNotExist) as e:return JsonResponse({'error':' '.join(e.messages) if isinstance(e,ValidationError) else 'Offline-Daten ungültig.'},status=409)
    return JsonResponse({'version':version,'status':'accepted'})

@login_required
@require_POST
def sync_note(request,meeting_id):
    try:
        data=json.loads(request.body)
        if set(data)!={'user_id','context_id','version','markdown'}:raise ValidationError('Notizdaten ungültig.')
        context=active_context(request)
        if not context or str(context.pk)!=data['context_id'] or str(request.user.pk)!=data['user_id']:raise PermissionDenied
        note=save_note(context,meeting_id,data['version'],data['markdown'])
    except (ValidationError,ValueError,KeyError,TypeError) as e:return JsonResponse({'error':' '.join(e.messages) if isinstance(e,ValidationError) else 'Notizdaten ungültig.'},status=409)
    return JsonResponse({'version':note.version})
