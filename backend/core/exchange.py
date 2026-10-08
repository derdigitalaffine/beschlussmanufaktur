"""Version 1: internally initiated, signed snapshots. No generic remote ORM writes."""
import hashlib,hmac,json,secrets,time,uuid,ssl
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from django.conf import settings
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction,IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Organization, RegistryRecord, Mandate, User, Membership, AccessGrant, ExchangeState, ExchangeNonce, ExchangePolicy, TransferBatch, PublicRecord, RemoteChange, Template, Publication, ExternalDocument, Attachment, ReplicaAsset

REMOTE_ROLES={'member','chair','clerk','mayor','local_mayor'}
MAX_BODY=8*1024*1024

def key(channel):
    value=getattr(settings,'EXCHANGE_'+channel.upper()+'_KEY','')
    if channel not in ('protected','public') or len(value)<32 or not settings.EXCHANGE_SOURCE:raise PermissionDenied('Übertragung ist nicht konfiguriert.')
    uuid.UUID(settings.EXCHANGE_SOURCE)
    return value.encode()

def encoded(data):return json.dumps(data,sort_keys=True,separators=(',',':')).encode()

def signed_headers(channel,method,path,body=b''):
    timestamp=str(int(time.time()));nonce=secrets.token_hex(24)
    material='\n'.join([method,path,timestamp,nonce,hashlib.sha256(body).hexdigest()]).encode()
    signature=hmac.new(key(channel),material,hashlib.sha256).hexdigest()
    return {'X-BM-Time':timestamp,'X-BM-Nonce':nonce,'X-BM-Signature':signature,'Content-Type':'application/json'}

def authorize(request,channel):
    secret=key(channel)
    timestamp=request.headers.get('X-BM-Time','');nonce=request.headers.get('X-BM-Nonce','')
    if abs(time.time()-int(timestamp))>300 or len(nonce)!=48:raise PermissionDenied
    if len(request.body)>MAX_BODY:raise ValidationError('Übertragung zu groß.')
    material='\n'.join([request.method,request.path,timestamp,nonce,hashlib.sha256(request.body).hexdigest()]).encode()
    if not hmac.compare_digest(hmac.new(secret,material,hashlib.sha256).hexdigest(),request.headers.get('X-BM-Signature','')):raise PermissionDenied
    try:
        with transaction.atomic():ExchangeNonce.objects.create(digest=hashlib.sha256((channel+nonce).encode()).hexdigest())
    except IntegrityError:raise PermissionDenied('Wiederholte Anfrage.')
    ExchangeNonce.objects.filter(created_at__lt=timezone.now()-timezone.timedelta(minutes=10)).delete()

def scalar(obj,fields):
    result={}
    for field in fields:
        value=getattr(obj,field)
        result[field]=value.isoformat() if hasattr(value,'isoformat') else str(value) if isinstance(value,uuid.UUID) else value
    return result

REGISTRY_FIELDS=['id','organization_id','kind','name','starts_on','ends_on','details','version','archived']
MANDATE_FIELDS=['id','committee_id','term_id','user_id','person_id','function_id','faction_id','substitutes_for_id','starts_on','ends_on','voting','archived','version']
MEMBERSHIP_FIELDS=['id','user_id','organization_id','role','starts_at','ends_at','revoked_at','version']
GRANT_FIELDS=['id','organization_id','membership_id','resource_kind','resource_id','actions','expires_at','revoked_at','reason']

def snapshot(channel):
    policies=ExchangePolicy.objects.filter(**{channel+'_enabled':True})
    orgs=Organization.objects.filter(pk__in=policies.values('organization_id'))
    ids=set(orgs.values_list('id',flat=True))
    if channel=='public':
        records=[{'id':str(o.pk),'organization_id':str(o.pk),'kind':'organization','title':o.name,'body':'','version':1,'attachments':[]} for o in orgs]
        records += [{'id':str(r.pk),'organization_id':str(r.organization_id),'kind':'committee','title':r.name,'body':'','version':r.version,'attachments':[]} for r in RegistryRecord.objects.filter(organization_id__in=ids,kind='committee',archived=False)]
        for publication in Publication.objects.filter(template__organization_id__in=ids,withdrawn_at__isnull=True).select_related('template'):
            version=publication.template.versions.get(version=publication.version)
            files=[a for a in version.snapshot['attachments'] if a['public'] and a['checked']]
            records.append({'id':str(publication.template_id),'organization_id':str(publication.template.organization_id),'kind':'template','title':publication.subject,'body':publication.markdown,'version':publication.version,'attachments':files})
        from .meeting_transfer import public_meetings
        records+=public_meetings(ids)
        from .models import Minutes
        for minutes in Minutes.objects.filter(meeting__organization_id__in=ids,published_version__isnull=False).select_related('meeting'):
            public=minutes.public_snapshot
            records.append({'id':str(minutes.pk),'organization_id':str(minutes.meeting.organization_id),'kind':'minutes','title':public['title'],'body':public['markdown'],'version':public['version'],'attachments':[]})
        from .models import PortalConfiguration
        from .portal_configuration import FIELDS
        portals=[scalar(p,FIELDS) for p in PortalConfiguration.objects.filter(organization_id__in=ids)]
        for portal in portals:portal['organizations']=[x for x in portal['organizations'] if uuid.UUID(x) in ids]
        return {'records':records,'portals':portals}
    memberships=Membership.objects.filter(organization_id__in=ids,role__in=REMOTE_ROLES)
    users=User.objects.filter(pk__in=memberships.values('user_id'))
    registry=RegistryRecord.objects.filter(organization_id__in=ids)
    from django.db.models import Q
    mandates=Mandate.objects.filter(committee_id__in=registry.values('pk')).filter(Q(user_id__in=users.values('pk'))|Q(user__isnull=True))
    # Substitution references must also be in this snapshot.
    mandate_ids=set(mandates.values_list('id',flat=True))
    rows=[]
    for m in mandates:
        row=scalar(m,MANDATE_FIELDS)
        if m.substitutes_for_id not in mandate_ids:row['substitutes_for_id']=None
        rows.append(row)
    documents=[]
    from .templates_service import template_access
    for obj in Template.objects.filter(organization_id__in=ids,state='ready').select_related('organization','kind','author','unit'):
        permissions={str(c.pk):[a for a in ('read','export','edit') if template_access(c,a,obj)] for c in memberships}
        permissions={k:v for k,v in permissions.items() if 'read' in v}
        if permissions:
            version=obj.versions.get(version=obj.version)
            documents.append({'id':str(obj.pk),'organization_id':str(obj.organization_id),'title':obj.subject,'markdown':obj.markdown,'number':obj.number,'version':obj.version,'permissions':permissions,'attachments':version.snapshot['attachments']})
    from .meeting_transfer import export_meetings
    meeting_data=export_meetings(ids,list(memberships),scalar)
    return {'meeting_data':meeting_data,'documents':documents,'organizations':[dict(id=str(o.pk),name=o.name,kind=o.kind,primary_parent_id=str(o.primary_parent_id) if o.primary_parent_id in ids else None) for o in orgs],
        'users':[scalar(u,['id','email','password','first_name','last_name','is_active']) for u in users],
        'memberships':[scalar(m,MEMBERSHIP_FIELDS) for m in memberships],
        'registry':[scalar(r,REGISTRY_FIELDS) for r in registry],
        'mandates':rows,
        'grants':[scalar(g,GRANT_FIELDS) for g in AccessGrant.objects.filter(membership__in=memberships).exclude(resource_kind='template')]}

def queue_snapshot(channel):
    if settings.SERVER_ROLE!='internal':raise PermissionDenied
    key(channel)
    with transaction.atomic():
        ExchangeState.objects.get_or_create(channel=channel)
        state=ExchangeState.objects.select_for_update().get(channel=channel)
        state.revision+=1;state.save()
        payload={'schema':1,'source':settings.EXCHANGE_SOURCE,'channel':channel,'revision':state.revision,'data':snapshot(channel)}
        return TransferBatch.objects.create(channel=channel,revision=state.revision,payload=payload)

def expect_keys(obj,allowed):
    if not isinstance(obj,dict) or set(obj)!=set(allowed):raise ValidationError('Unzulässige Felder im Übertragungsvertrag.')

def upsert(model,rows,fields):
    for row in rows:
        expect_keys(row,fields)
        data=dict(row);identifier=data.pop('id')
        instance=model.objects.filter(pk=identifier).first() or model(pk=identifier)
        for name,value in data.items():
            field=model._meta.get_field(name)
            setattr(instance,name,field.target_field.to_python(value) if field.is_relation else field.to_python(value))
        instance.full_clean();instance.save()

@transaction.atomic
def receive(payload,channel):
    expect_keys(payload,['schema','source','channel','revision','data'])
    if payload['schema']!=1 or payload['source']!=settings.EXCHANGE_SOURCE or payload['channel']!=channel or not isinstance(payload['revision'],int) or payload['revision']<1:raise ValidationError('Falsche Quelle, Version oder Kanal.')
    ExchangeState.objects.get_or_create(channel=channel)
    state=ExchangeState.objects.select_for_update().get(channel=channel)
    if payload['revision']<state.revision:raise ValidationError('Veralteter Stand.')
    if payload['revision']==state.revision:return
    data=payload['data']
    if channel=='public':
        data.setdefault('portals',[])
        expect_keys(data,['records','portals'])
        from .models import PortalConfiguration
        from .portal_configuration import FIELDS
        PortalConfiguration.objects.all().delete()
        upsert(PortalConfiguration,data['portals'],FIELDS)
        for row in data['records']:
            row.setdefault('metadata',{})
            expect_keys(row,['id','organization_id','kind','title','body','version','attachments','metadata'])
            from .public_portal import validate_metadata
            validate_metadata(row['metadata'], row['kind'])
            if row['kind'] not in ('organization','committee','template','meeting','minutes'):raise ValidationError('Unzulässiges öffentliches Objekt.')
        upsert(PublicRecord,data['records'],['id','organization_id','kind','title','body','version','attachments','metadata'])
        PublicRecord.objects.exclude(pk__in=[row['id'] for row in data['records']]).delete()
    else:
        expect_keys(data,['organizations','users','memberships','registry','mandates','grants','documents','meeting_data'])
        # Receiver is a dedicated replica; public storage never reaches this branch.
        org_ids={row['id'] for row in data['organizations']};user_ids={row['id'] for row in data['users']}
        for row in data['users']:
            expect_keys(row,['id','email','password','first_name','last_name','is_active'])
            existing=User.objects.filter(pk=row['id']).first()
            if existing and not existing.exchange_managed:raise ValidationError('Lokales Konto darf nicht überschrieben werden.')
            if not isinstance(row['password'],str) or len(row['password'])>256:raise ValidationError('Ungültiger Passwort-Hash.')
            if not row['password'].startswith('!') and identify_hasher(row['password']).algorithm not in ('pbkdf2_sha256','pbkdf2_sha1','argon2','scrypt'):raise ValidationError('Ungültiger Passwort-Hash.')
            defaults=dict(row);defaults.pop('id');defaults.update(username='replica-'+str(row['id']),exchange_managed=True,is_staff=False,is_superuser=False)
            User.objects.update_or_create(pk=row['id'],defaults=defaults)
        for row in data['organizations']:
            expect_keys(row,['id','name','kind','primary_parent_id'])
            if row['primary_parent_id'] and row['primary_parent_id'] not in org_ids:raise ValidationError('Fremde Hauptzuordnung.')
            Organization.objects.update_or_create(pk=row['id'],defaults={'name':row['name'],'kind':row['kind']})
        for row in data['organizations']:Organization.objects.filter(pk=row['id']).update(primary_parent_id=row['primary_parent_id'])
        for o in Organization.objects.filter(pk__in=org_ids):o.full_clean()
        for row in data['memberships']:
            if row['role'] not in REMOTE_ROLES or row['organization_id'] not in org_ids or row['user_id'] not in user_ids:raise ValidationError('Unzulässiger externer Arbeitskontext.')
        for row in data['registry']:
            if row['organization_id'] not in org_ids:raise ValidationError('Fremder Datensatz.')
        upsert(Membership,data['memberships'],MEMBERSHIP_FIELDS)
        upsert(RegistryRecord,data['registry'],REGISTRY_FIELDS)
        # End previously transferred access even when its organization is no longer enabled.
        Membership.objects.exclude(pk__in=[r['id'] for r in data['memberships']]).update(revoked_at=timezone.now())
        User.objects.filter(exchange_managed=True).exclude(pk__in=user_ids).update(is_active=False)
        mandate_rows=sorted(data['mandates'],key=lambda x:bool(x['substitutes_for_id']))
        upsert(Mandate,mandate_rows,MANDATE_FIELDS)
        Mandate.objects.exclude(pk__in=[r['id'] for r in mandate_rows]).update(archived=True)
        AccessGrant.objects.all().delete()
        upsert(AccessGrant,data['grants'],GRANT_FIELDS)
        member_ids={str(r['id']) for r in data['memberships']}
        for doc in data['documents']:
            expect_keys(doc,['id','organization_id','title','markdown','number','version','permissions','attachments'])
            if doc['organization_id'] not in org_ids or set(doc['permissions'])-member_ids:raise ValidationError('Unzulässige Vorlagenfreigabe.')
            for rights in doc['permissions'].values():
                if not isinstance(rights,list) or set(rights)-{'read','export','edit'}:raise ValidationError('Unzulässiges Vorlagenrecht.')
        upsert(ExternalDocument,data['documents'],['id','organization_id','title','markdown','number','version','permissions','attachments'])
        from .meeting_transfer import import_meetings
        import_meetings(data['meeting_data'],upsert,expect_keys,member_ids)
        ExternalDocument.objects.exclude(pk__in=[d['id'] for d in data['documents']]).delete()
    # Files no longer referenced by the current replica are removed with withdrawal.
    from .meeting_transfer import referenced_assets
    asset_ids=[a['id'] for a in referenced_assets(channel)]
    ReplicaAsset.objects.exclude(pk__in=asset_ids).delete()
    state.revision=payload['revision'];state.received_at=timezone.now();state.save()

@csrf_exempt
@require_http_methods(['POST'])
def inbox(request):
    channel=settings.SERVER_ROLE
    if channel not in ('protected','public'):raise PermissionDenied
    try:
        authorize(request,channel);receive(json.loads(request.body),channel)
    except PermissionDenied:return JsonResponse({'error':'unauthorized'},status=403)
    except (ValueError,KeyError,TypeError,ValidationError,IntegrityError):return JsonResponse({'error':'invalid-transfer'},status=400)
    return JsonResponse({'status':'accepted'})

@csrf_exempt
@require_http_methods(['GET'])
def events(request):
    if settings.SERVER_ROLE!='protected':raise PermissionDenied
    try:authorize(request,'protected')
    except (PermissionDenied,ValueError):return JsonResponse({'error':'unauthorized'},status=403)
    rows=RemoteChange.objects.filter(state='pending').order_by('created_at')[:100]
    return JsonResponse({'events':[scalar(r,['id','organization_id','resource_id','resource_kind','base_version','context_id','actor_id','content','reason','created_at']) for r in rows]})

def transport(channel,path,body=None):
    if settings.SERVER_ROLE!='internal':raise PermissionDenied
    origin=getattr(settings,'EXCHANGE_'+channel.upper()+'_URL','').rstrip('/')
    parsed=urlparse(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:raise ValidationError('Fester HTTPS-Origin erforderlich.')
    ssl_context=ssl.create_default_context(cafile=settings.EXCHANGE_CA_FILE or None)
    method='POST' if body is not None else 'GET';payload=encoded(body) if body is not None else b''
    class NoRedirect(__import__('urllib.request',fromlist=['HTTPRedirectHandler']).HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise ValidationError('Umleitung des Übertragungskanals abgewiesen.')
    import urllib.request
    opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl_context),urllib.request.ProxyHandler({}))
    with opener.open(Request(origin+path,data=payload if method=='POST' else None,method=method,headers=signed_headers(channel,method,path,payload)),timeout=20) as response:
        raw=response.read(MAX_BODY+1)
        if len(raw)>MAX_BODY:raise ValidationError('Antwort zu groß.')
        return json.loads(raw)

def deliver(batch):
    # A dedicated single worker takes batches in revision order. Retries are idempotent.
    batch.attempts+=1;batch.save(update_fields=['attempts'])
    try:transport(batch.channel,'/transfer/inbox/',batch.payload)
    except Exception:
        batch.error='Übertragung fehlgeschlagen; Verbindung und Konfiguration prüfen.';batch.save(update_fields=['error']);return False
    try:
        data=batch.payload['data']
        documents=data['records'] if batch.channel=='public' else data['documents']
        if batch.channel=='protected':
            documents=documents+[{'attachments':item['template']['attachments']} for inv in data['meeting_data']['invitations'] for item in inv['snapshot']['items'] if item.get('template')]
        sent=set()
        for manifest in documents:
            for meta in manifest.get('attachments',[]):
                if meta['id'] in sent:continue
                sent.add(meta['id'])
                asset=Attachment.objects.filter(pk=meta['id'],digest=meta['digest']).first()
                if not asset:raise ValidationError('Anlage nicht verfügbar.')
                import base64
                with asset.file.open('rb') as file:
                    transport(batch.channel,'/transfer/assets/',{'id':meta['id'],'digest':meta['digest'],'data':base64.b64encode(file.read()).decode()})
    except Exception:
        batch.error='Dateiübertragung fehlgeschlagen; Wiederholung ausstehend.';batch.save(update_fields=['error']);return False
    batch.delivered_at=timezone.now();batch.error='';batch.save(update_fields=['delivered_at','error']);return True

def pull_events():
    data=transport('protected','/transfer/events/')
    expect_keys(data,['events'])
    for row in data['events']:
        expect_keys(row,['id','organization_id','resource_id','resource_kind','base_version','context_id','actor_id','content','reason','created_at'])
        if row['resource_kind'] not in ('registry','template'):raise ValidationError('Unbekannte Änderungsart.')
        # Arrival never applies a change to authoritative content.
        if len(row['content'])>100000 or len(row['reason'])>500:raise ValidationError('Änderung zu groß.')
        RemoteChange.objects.get_or_create(pk=row['id'],defaults={k:v for k,v in row.items() if k!='id'})
    if data['events']:transport('protected','/transfer/ack/',{'ids':[r['id'] for r in data['events']]})


@csrf_exempt
@require_http_methods(['POST'])
def acknowledge(request):
    if settings.SERVER_ROLE!='protected':raise PermissionDenied
    try:
        authorize(request,'protected');data=json.loads(request.body);expect_keys(data,['ids'])
        if not isinstance(data['ids'],list) or len(data['ids'])>100:raise ValidationError('Zu viele IDs.')
        RemoteChange.objects.filter(pk__in=data['ids'],state='pending').update(state='collected')
    except (ValueError,TypeError,ValidationError,PermissionDenied):return JsonResponse({'error':'invalid'},status=400)
    return JsonResponse({'status':'acknowledged'})


@csrf_exempt
@require_http_methods(['POST'])
def receive_asset(request):
    channel=settings.SERVER_ROLE
    if channel not in ('public','protected'):raise PermissionDenied
    try:
        authorize(request,channel);data=json.loads(request.body);expect_keys(data,['id','digest','data'])
        import base64
        binary=base64.b64decode(data['data'],validate=True)
        if len(binary)>4*1024*1024 or hashlib.sha256(binary).hexdigest()!=data['digest']:raise ValidationError('Ungültige Datei.')
        from .meeting_transfer import referenced_assets
        if not any(a['id']==data['id'] and a['digest']==data['digest'] for a in referenced_assets(channel)):raise PermissionDenied
        ReplicaAsset.objects.update_or_create(pk=data['id'],defaults={'digest':data['digest'],'data':binary})
    except (ValueError,TypeError,KeyError,ValidationError,PermissionDenied):return JsonResponse({'error':'invalid-asset'},status=400)
    return JsonResponse({'status':'accepted'})
