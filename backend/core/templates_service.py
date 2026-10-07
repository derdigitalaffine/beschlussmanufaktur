import hashlib,json,re,io,zipfile
from datetime import date
import bleach,markdown as markdown_library
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Template,TemplateVersion,TemplateKind,TemplateParticipant,Membership,AccessGrant,Mandate,Attachment,AuditEvent,Notification,EditPresence,Organization,RegistryRecord
from .permissions import available_contexts,can_access

DEFAULT_KINDS=['Beschlussvorlage','Mitteilung','Antrag','Anfrage','Einwohnerfrage','Dringlichkeitsvorlage','Änderungsvorlage','Tischvorlage']
DEFAULT_TEXT='## Sachverhalt\n\n\n## Begründung\n\n\n## Beschlussvorschlag\n\n\n## Finanzielle Auswirkungen\n\n'
ALLOWED_TAGS=['p','br','strong','em','ul','ol','li','blockquote','pre','code','h1','h2','h3','h4','table','thead','tbody','tr','th','td','hr','a','sup']

def render_markdown(text):
    # No image/network fetching, executable HTML, or user CSS. Escaped text remains visible.
    html=markdown_library.markdown(text,extensions=['tables','fenced_code','footnotes'])
    return bleach.clean(html,tags=ALLOWED_TAGS,attributes={'a':['href','title']},protocols=['https','mailto'],strip=True)

def validate_configuration(fields,workflow):
    if not isinstance(fields,list) or len(fields)>40:raise ValidationError('Maximal 40 Zusatzfelder.')
    keys=set()
    for field in fields:
        if not isinstance(field,dict) or set(field)-{'key','label','type','required','section','choices'} or not re.fullmatch('[a-z][a-z0-9_]{0,39}',field.get('key','')) or field['key'] in keys:raise ValidationError('Zusatzfelder benötigen eindeutige Schlüssel.')
        keys.add(field['key'])
        if field.get('type','text') not in ('text','number','date','choice','boolean'):raise ValidationError('Unbekannter Feldtyp.')
        if not isinstance(field.get('label'),str) or len(field['label'])>100:raise ValidationError('Feldbeschriftung fehlt.')
    if not isinstance(workflow,list) or len(workflow)>12:raise ValidationError('Maximal zwölf Prüfschritte.')
    for step in workflow:
        if not isinstance(step,dict) or set(step)-{'name','role','group','condition','substitute'} or step.get('role') not in ('reviewer','release','clerk') or not step.get('name'):raise ValidationError('Ungültiger Prüfschritt.')
        if 'condition' in step and (not isinstance(step['condition'],dict) or set(step['condition'])!={'field','equals'} or step['condition']['field'] not in keys):raise ValidationError('Bedingung muss sich auf ein Zusatzfeld beziehen.')
        if 'group' in step and (not isinstance(step['group'],int) or not 1<=step['group']<=100):raise ValidationError('Prüfgruppe muss zwischen 1 und 100 liegen.')
        if 'substitute' in step and step['substitute'] not in ('reviewer','release','clerk'):raise ValidationError('Ungültige Vertretungsrolle.')

def template_access(context,action,obj):
    if not context or not available_contexts(context.user).filter(pk=context.pk).exists():return False
    same=context.organization_id==obj.organization_id
    if same and can_access(context,action,'template',obj):return True
    if same and action in ('read','review'):
        from .workflow import step_access
        if any(step_access(context,step) for step in obj.review_steps.filter(version=obj.version,state='pending').select_related('template')):return True
    if same and context.role=='clerk' and action in ('read','edit','export','review','release','publish','delegate'):return True
    if same and obj.author_id==context.user_id and context.role=='author' and action in ('read','edit','export','delegate'):return True
    if same and TemplateParticipant.objects.filter(template=obj,membership=context,revoked_at__isnull=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).exists():
        participant=TemplateParticipant.objects.get(template=obj,membership=context)
        if action in participant.actions:return True
    if action in ('read','export') and obj.state in ('ready','withdrawn') and obj.classification in ('committee','public_planned'):
        today=timezone.localdate()
        return obj.consultations.filter(committee__organization_id=context.organization_id,committee__mandates__user_id=context.user_id,committee__mandates__archived=False,committee__mandates__starts_on__lte=today,committee__mandates__ends_on__gte=today).exists()
    if same and obj.unit and can_access(context,action,'unit',obj.unit):return True
    return False

def snapshot(obj):
    return {'subject':obj.subject,'markdown':obj.markdown,'public_markdown':obj.public_markdown,'fields':obj.fields,'reference':obj.reference,'classification':obj.classification,'kind':obj.kind.name,'unit':str(obj.unit_id) if obj.unit_id else None,'attachments':[{'id':str(a.pk),'name':a.name,'digest':a.digest,'public':a.public,'checked':a.checked,'size':a.size,'media_type':a.media_type} for a in obj.attachments.filter(removed_at__isnull=True)],'consultations':[{'id':str(c.pk),'committee':str(c.committee_id),'position':c.position,'deciding':c.deciding,'public':c.public,'may_amend':c.may_amend,'amendment':c.amendment,'version':c.version} for c in obj.consultations.all()]}

def archive(obj,user,reason):
    data=snapshot(obj)
    return TemplateVersion.objects.create(template=obj,version=obj.version,snapshot=data,digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),author=user,reason=reason)

def notify(obj,actor):
    users={obj.author_id}|set(obj.participants.filter(revoked_at__isnull=True).values_list('membership__user_id',flat=True))
    for user_id in users-{actor.pk}:Notification.objects.create(user_id=user_id,text='Eine beteiligte Vorlage wurde geändert.',path=f'/vorlagen/{obj.pk}/')

def touch(obj,user,reason):
    obj.version+=1
    if obj.state!='draft':obj.state='draft'
    obj.save();archive(obj,user,reason);notify(obj,user)
    AuditEvent.objects.create(actor=user,action='template.version',object_id=str(obj.pk),metadata={'version':obj.version,'reason':reason})

def ensure_defaults(org):
    for name in DEFAULT_KINDS:TemplateKind.objects.get_or_create(organization=org,name=name,defaults={'initial_markdown':DEFAULT_TEXT})

def lock_template(context,obj_id,action,expected):
    obj=Template.objects.select_for_update(of=('self',)).select_related('kind','organization','author','unit').get(pk=obj_id)
    if not template_access(context,action,obj):raise PermissionDenied
    if obj.version!=expected:raise ValidationError('Zwischenzeitlich geändert. Ihr Text bleibt im Formular; vergleichen Sie den aktuellen Stand und speichern Sie erneut.')
    return obj

def validate_upload(upload):
    if upload.size>4*1024*1024:raise ValidationError('Maximal 4 MiB je Anlage.')
    data=upload.read();upload.seek(0)
    name=upload.name.rsplit('/',1)[-1].rsplit('\\',1)[-1][:200]
    suffix=name.lower().rsplit('.',1)[-1]
    media={'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','txt':'text/plain'}.get(suffix)
    if not media:raise ValidationError('Erlaubt sind PDF, PNG, JPEG, DOCX und UTF-8-Text.')
    if suffix=='pdf' and not data.startswith(b'%PDF-'):raise ValidationError('Keine gültige PDF-Kennung.')
    if suffix=='png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValidationError('Keine gültige PNG-Kennung.')
    if suffix in ('jpg','jpeg') and not data.startswith(b'\xff\xd8\xff'):raise ValidationError('Keine gültige JPEG-Kennung.')
    if suffix=='txt':
        try:data.decode('utf-8')
        except UnicodeDecodeError:raise ValidationError('Text muss UTF-8 sein.')
    if suffix=='docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(i.file_size for i in z.infolist())>20*1024*1024 or len(z.infolist())>2000 or 'word/document.xml' not in z.namelist() or any('vba' in n.lower() for n in z.namelist()):raise ValidationError('Ungültiges oder zu großes DOCX.')
        except zipfile.BadZipFile:raise ValidationError('Kein gültiges DOCX.')
    return name,media,hashlib.sha256(data).hexdigest()
