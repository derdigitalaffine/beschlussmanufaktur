import hashlib,json
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.db.models import Q,Max
from django.utils import timezone
from .models import Meeting,AgendaItem,MeetingInvitation,InvitationDelivery,MeetingGuest,MeetingAmendment,Membership,Mandate,Template,Notification,AuditEvent
from .permissions import available_contexts
from .templates_service import template_access


def meeting_access(context,action,obj):
    if not context or not available_contexts(context.user).filter(pk=context.pk).exists():return False
    if settings.SERVER_ROLE=='protected':return action in obj.permission_snapshot.get(str(context.pk),[])
    same=context.organization_id==obj.organization_id
    if not same:return False
    if context.role=='clerk':return action in ('read','private','plan','invite','export','live','protocol')
    if context.user_id==obj.chair_id:return action in ('read','private','plan','export','chair','live','protocol')
    if context.user_id==obj.scribe_id:return action in ('read','private','export','live','protocol')
    today=timezone.localdate()
    if obj.state!='preparation' and action in ('read','private','export') and Mandate.objects.filter(committee=obj.committee,user=context.user,archived=False,starts_on__lte=today,ends_on__gte=today).exists():return True
    guest=MeetingGuest.objects.filter(meeting=obj,membership=context,expires_at__gt=timezone.now()).first()
    return bool(guest and (action in ('read','export') or action=='private' and guest.private))


def lock_meeting(context,meeting_id,action,version):
    obj=Meeting.objects.select_for_update(of=('self',)).select_related('organization','committee','chair','scribe','room').get(pk=meeting_id)
    if not meeting_access(context,action,obj):raise PermissionDenied
    if obj.leading_server!=settings.SERVER_ROLE:raise ValidationError('Die Sitzung wird auf dem anderen Server geführt. Dort bearbeiten oder eine kontrollierte Rückgabe durchführen.')
    if obj.version!=version:raise ValidationError('Sitzungsstand wurde geändert. Bitte neu laden; der vorherige Versandstand bleibt erhalten.')
    return obj


def meeting_snapshot(obj,context=None):
    private=context is None or meeting_access(context,'private',obj)
    result={'id':str(obj.pk),'title':obj.title,'committee':obj.committee.name,'organization':obj.organization.name,'starts_at':obj.starts_at.isoformat(),'ends_at':obj.ends_at.isoformat(),'location':obj.location,'chair':obj.chair.get_full_name() or obj.chair.email,'scribe':obj.scribe.get_full_name() or obj.scribe.email,'version':obj.version,'state':obj.state,'items':[]}
    for item in obj.items.filter(removed=False).select_related('template'):
        if not item.public and not private:continue
        data={'id':str(item.pk),'parent':str(item.parent_id) if item.parent_id else None,'position':item.position,'title':item.title,'public':item.public,'markdown':item.markdown,'estimated_minutes':item.estimated_minutes,'template':None}
        if item.template_id and (context is None or template_access(context,'read',item.template)):
            v=item.template.versions.get(version=item.template.version)
            data['template']={'id':str(item.template_id),'number':item.template.number,'version':v.version,'subject':v.snapshot['subject'],'markdown':v.snapshot['markdown'],'attachments':v.snapshot['attachments']}
        if item.frozen_template and context is not None:
            from .models import ExternalDocument
            document=ExternalDocument.objects.filter(pk=item.frozen_template.get('id')).first()
            if document and 'read' in document.permissions.get(str(context.pk),[]):data['template']=item.frozen_template
        result['items'].append(data)
    return result


def paper_markdown(data):
    text=f"# Einladung\n\n{data['committee']}\n\nTermin: {data['starts_at']}\n\nOrt: {data['location']}\n\n## Tagesordnung\n\n"
    for item in data['items']:text+=f"{item['position']}. {'Öffentlich' if item['public'] else 'Nichtöffentlich'}: {item['title']}\n\n"
    for item in data['items']:
        text+=f"## TOP {item['position']} · {item['title']}\n\n{item['markdown']}\n\n"
        if item['template']:text+=f"### {item['template']['number']} · {item['template']['subject']} · Version {item['template']['version']}\n\n{item['template']['markdown']}\n\n"
    return text


def eligible_contexts(obj):
    # Exactly one context is used for each recipient snapshot; roles are never unioned.
    contexts=Membership.objects.filter(organization=obj.organization).select_related('user').order_by('user_id','id')
    return [c for c in contexts if meeting_access(c,'read',obj)]


@transaction.atomic
def issue(context,meeting_id,version,reason='',exception_confirmed=False):
    obj=lock_meeting(context,meeting_id,'invite',version)
    if obj.state not in ('preparation','invited'):raise ValidationError('Einladung ist nur in der Vorbereitungsphase möglich.')
    now=timezone.now()
    if obj.starts_at<=now:raise ValidationError('Sitzungsbeginn liegt nicht in der Zukunft.')
    if obj.state=='invited' and not reason.strip():raise ValidationError('Erneuter Versand benötigt eine Begründung.')
    full_days=(timezone.localtime(obj.starts_at).date()-timezone.localtime(now).date()).days-1
    if full_days<obj.invitation_days and (not reason.strip() or not exception_confirmed):raise ValidationError('Einladungsfrist unterschritten. Begründete und bestätigte Ausnahme erforderlich.')
    if not obj.items.filter(removed=False).exists():raise ValidationError('Tagesordnung fehlt.')
    for item in obj.items.filter(removed=False,template__isnull=False).select_related('template'):
        if item.template.state!='ready':raise ValidationError('Alle verknüpften Vorlagen müssen intern bereitgestellt sein.')
        if item.template.attachments.filter(removed_at__isnull=True,checked=False).exists():raise ValidationError('Ungeprüfte Anlagen.')
    obj.state='invited';obj.version+=1;obj.save()
    data=meeting_snapshot(obj);revision=(obj.invitations.aggregate(n=Max('revision'))['n'] or 0)+1
    invitation=MeetingInvitation.objects.create(meeting=obj,revision=revision,snapshot=data,digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),reason=reason[:1000],issued_by=context.user)
    seen=set()
    for recipient in eligible_contexts(obj):
        if recipient.user_id in seen:continue
        seen.add(recipient.user_id)
        personal=meeting_snapshot(obj,recipient);personal['context_id']=str(recipient.pk)
        InvitationDelivery.objects.create(invitation=invitation,user=recipient.user,snapshot=personal)
        Notification.objects.create(user=recipient.user,text='Eine Sitzungseinladung oder ein Nachtrag liegt vor.',path=f'/sitzungen/{obj.pk}/')
    AuditEvent.objects.create(actor=context.user,action='meeting.invited',object_id=str(obj.pk),metadata={'revision':revision,'digest':invitation.digest,'exception':exception_confirmed,'reason':reason})
    return invitation


@transaction.atomic
def save_item(context,meeting_id,version,data,item_id=None):
    obj=lock_meeting(context,meeting_id,'plan',version)
    if obj.state!='preparation':raise ValidationError('Nach Einladung sind Änderungen nur über den Nachtragsvorgang zulässig.')
    item=AgendaItem.objects.get(pk=item_id,meeting=obj) if item_id else AgendaItem(meeting=obj,proposed_by=context.user)
    for name,value in data.items():setattr(item,name,value)
    if item.template and not template_access(context,'read',item.template):raise PermissionDenied
    item.full_clean();item.save();obj.version+=1;obj.save(update_fields=['version'])
    AuditEvent.objects.create(actor=context.user,action='agenda.saved',object_id=str(item.pk),metadata={'meeting':str(obj.pk),'version':obj.version,'title':item.title,'public':item.public,'parent':str(item.parent_id) if item.parent_id else None})
    return item


@transaction.atomic
def approve_amendment(context,change_id,decision_record):
    change=MeetingAmendment.objects.select_related('meeting').get(pk=change_id)
    obj=lock_meeting(context,change.meeting_id,'chair',change.base_version)
    change=MeetingAmendment.objects.select_for_update().get(pk=change_id)
    if change.state!='pending' or obj.state!='invited':raise ValidationError('Nachtrag ist nicht mehr aktuell.')
    if not decision_record.strip():raise ValidationError('Feststellung, Beschluss oder rechtliche Grundlage dokumentieren.')
    if change.kind=='urgent':
        item=AgendaItem(meeting=obj,proposed_by=change.requested_by,title=change.data['title'],public_title=change.data.get('public_title',''),public=change.data['public'],markdown=change.data.get('markdown',''),position=change.data['position']);item.full_clean();item.save()
    elif change.kind in ('correction','remove','attachment'):
        item=AgendaItem.objects.get(pk=change.data['item_id'],meeting=obj)
        if change.kind=='remove':item.removed=True
        elif change.kind=='correction':item.title=change.data['title'];item.public_title=change.data.get('public_title',item.public_title)
        else:
            template=Template.objects.get(pk=change.data['template_id'])
            if not template_access(context,'read',template) or template.state!='ready':raise PermissionDenied
            item.template=template
        item.full_clean();item.save()
    elif change.kind=='reschedule':
        from django.utils.dateparse import parse_datetime
        obj.starts_at=parse_datetime(change.data['starts_at']);obj.ends_at=parse_datetime(change.data['ends_at']);obj.full_clean();obj.save()
    change.state='approved';change.reviewed_by=context.user;change.decision_record=decision_record[:1000];change.save()
    # The chair approves, the assigned clerk initiates a new issue separately.
    obj.version+=1;obj.save(update_fields=['version'])
    AuditEvent.objects.create(actor=context.user,action='meeting.amendment',object_id=str(obj.pk),metadata={'change':str(change.pk),'kind':change.kind,'reason':change.reason,'decision':decision_record[:1000]})
    return obj
