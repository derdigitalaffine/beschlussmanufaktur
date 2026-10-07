from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.utils import timezone
from .models import ReviewStep,Template,TemplateVersion,NumberSequence,Publication,Organization,Membership,AuditEvent,Attachment,TemplateComment,Notification
from .templates_service import lock_template,template_access,notify
from .permissions import available_contexts

DEFAULT_WORKFLOW=[{'name':'Fachliche Prüfung','role':'reviewer','group':1},{'name':'Interne Bereitstellung','role':'clerk','group':2}]

def step_access(context,step):
    return bool(context and available_contexts(context.user).filter(pk=context.pk).exists() and context.organization_id==step.template.organization_id and step.version==step.template.version and step.template.state=='review' and (step.assigned_id==context.pk if step.assigned_id else context.role in (step.role,step.substitute)))

@transaction.atomic
def submit(context,template_id,version):
    obj=lock_template(context,template_id,'edit',version)
    if obj.state=='review':raise ValidationError('Diese Fassung befindet sich bereits in Prüfung.')
    obj.review_steps.filter(version=obj.version,state='pending').update(state='superseded')
    config=obj.kind.workflow or DEFAULT_WORKFLOW
    for position,spec in enumerate(config):
        condition=spec.get('condition')
        if condition and obj.fields.get(condition['field'])!=condition['equals']:continue
        ReviewStep.objects.create(template=obj,version=obj.version,name=spec['name'],role=spec['role'],group=spec.get('group',position+1),substitute=spec.get('substitute',''))
    if not obj.review_steps.filter(version=obj.version,state='pending').exists():raise ValidationError('Mindestens ein wirksamer Prüfschritt erforderlich.')
    obj.state='review';obj.save(update_fields=['state'])
    notify(obj,context.user)
    for member in Membership.objects.filter(organization=obj.organization,role__in={'reviewer','clerk','release'}):
        if available_contexts(member.user).filter(pk=member.pk).exists():Notification.objects.create(user=member.user,text='Eine Vorlage wartet auf Prüfung.',path=f'/vorlagen/{obj.pk}/')
    AuditEvent.objects.create(actor=context.user,action='template.submitted',object_id=str(obj.pk),metadata={'version':obj.version})
    return obj

@transaction.atomic
def decide(context,step_id,version,decision,comment):
    initial=ReviewStep.objects.select_related('template').get(pk=step_id)
    Organization.objects.select_for_update().get(pk=initial.template.organization_id)
    obj=Template.objects.select_for_update().get(pk=initial.template_id)
    step=ReviewStep.objects.select_for_update().select_related('template').get(pk=step_id)
    if not step_access(context,step):raise PermissionDenied
    if obj.version!=version or step.state!='pending':raise ValidationError('Prüfstand ist nicht mehr aktuell.')
    if obj.review_steps.filter(version=obj.version,group__lt=step.group,state='pending').exists():raise ValidationError('Vorherige Prüfschritte sind noch offen.')
    if obj.kind.four_eyes and (obj.author_id==context.user_id or obj.review_steps.filter(version=obj.version,decided_by=context.user,state='approved').exists()):raise ValidationError('Vieraugenregel: Eine weitere Person muss prüfen.')
    if decision not in ('approve','return'):raise ValidationError('Unbekannte Entscheidung.')
    if decision=='return' and not comment.strip():raise ValidationError('Rückgabe benötigt eine Begründung.')
    step.state='approved' if decision=='approve' else 'returned';step.decided_by=context.user;step.decided_at=timezone.now();step.comment=comment[:1000];step.save()
    if decision=='return':obj.state='returned'
    elif not obj.review_steps.filter(version=obj.version,state='pending').exists():
        if obj.attachments.filter(removed_at__isnull=True,checked=False).exists():raise ValidationError('Ungeprüfte Anlagen verhindern die interne Bereitstellung.')
        if not obj.number:
            year=timezone.localdate().year
            NumberSequence.objects.get_or_create(organization=obj.organization,year=year)
            seq=NumberSequence.objects.select_for_update().get(organization=obj.organization,year=year);seq.value+=1;seq.save()
            obj.number_year=year;obj.number_sequence=seq.value;obj.number=f'{year}/{seq.value:04d}'
        obj.state='ready'
    obj.save()
    AuditEvent.objects.create(actor=context.user,action='template.review',object_id=str(obj.pk),metadata={'version':obj.version,'step':step.pk,'decision':decision,'comment':comment[:1000]});notify(obj,context.user)
    return obj

@transaction.atomic
def publish(context,template_id,version,withdraw=False):
    obj=lock_template(context,template_id,'publish',version)
    if withdraw:
        Publication.objects.filter(template=obj,withdrawn_at__isnull=True).update(withdrawn_at=timezone.now());obj.published_version=None
    else:
        if obj.state!='ready' or obj.classification!='public_planned' or not obj.public_markdown.strip():raise ValidationError('Bereitgestellte, öffentlich vorgesehene Vorlage mit gesonderter öffentlicher Fassung erforderlich.')
        # Optional second person; the reviewed internal and separately examined public text are one fixed version.
        if obj.kind.four_eyes and obj.author_id==context.user_id:raise ValidationError('Öffentliche Freigabe benötigt eine andere Person.')
        Publication.objects.filter(template=obj,withdrawn_at__isnull=True).update(withdrawn_at=timezone.now())
        Publication.objects.create(template=obj,version=obj.version,subject=obj.subject,markdown=obj.public_markdown,approved_by=context.user)
        obj.published_version=obj.version
    obj.save(update_fields=['published_version'])
    AuditEvent.objects.create(actor=context.user,action='publication.withdrawn' if withdraw else 'publication.released',object_id=str(obj.pk),metadata={'version':version})
    return obj
