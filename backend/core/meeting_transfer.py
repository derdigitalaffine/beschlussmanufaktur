"""Explicit meeting replication contract. Administration stays internal."""
import hashlib,json
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Meeting,AgendaItem,MeetingInvitation,InvitationDelivery,MeetingGuest,ExternalDocument
from .meetings_service import meeting_access,meeting_snapshot

MEETING_FIELDS=['id','organization_id','committee_id','title','starts_at','ends_at','room_id','location','chair_id','scribe_id','created_by_id','state','paused','version','rules','statutory_count','invitation_days','proposal_deadline','release_deadline','public_notice','public_enabled','leading_server','permission_snapshot','authority_base']
ITEM_FIELDS=['id','meeting_id','parent_id','position','title','public_title','public','markdown','estimated_minutes','proposed_by_id','removed','frozen_template']
INVITE_FIELDS=['id','meeting_id','revision','snapshot','digest','reason','issued_by_id','created_at']
DELIVERY_FIELDS=['id','invitation_id','user_id','snapshot','delivered_at','seen_at','error','attempts']

def export_meetings(org_ids,memberships,scalar):
    meetings=[];items=[];invitations=[];deliveries=[];journals=[]
    user_ids={c.user_id for c in memberships}
    for obj in Meeting.objects.filter(organization_id__in=org_ids).exclude(state='preparation').select_related('committee','chair','scribe'):
        if obj.chair_id not in user_ids or obj.scribe_id not in user_ids:continue
        row=scalar(obj,MEETING_FIELDS)
        row['created_by_id']=obj.scribe_id
        row['permission_snapshot']={str(c.pk):[a for a in ('read','private','export','live','chair','protocol') if meeting_access(c,a,obj)] for c in memberships}
        row['permission_snapshot']={k:v for k,v in row['permission_snapshot'].items() if 'read' in v}
        meetings.append(row)
        if obj.leading_server=='internal':
            from .session_transfer import bundle
            journals.append(bundle(obj,user_ids))
        latest=obj.invitations.order_by('-revision').first()
        frozen={i['id']:i.get('template') for i in latest.snapshot['items']} if latest else {}
        for item in obj.items.all():
            data=scalar(item,ITEM_FIELDS);data['proposed_by_id']=obj.scribe_id;data['frozen_template']=frozen.get(str(item.pk)) or {}
            items.append(data)
        for invitation in obj.invitations.all():
            data=scalar(invitation,INVITE_FIELDS);data['issued_by_id']=obj.scribe_id;invitations.append(data)
            for delivery in invitation.deliveries.filter(user_id__in=user_ids):deliveries.append(scalar(delivery,DELIVERY_FIELDS))
    return {'meetings':meetings,'items':items,'invitations':invitations,'deliveries':deliveries,'journals':journals}

def import_meetings(data,upsert,expect_keys,member_ids):
    expect_keys(data,['meetings','items','invitations','deliveries','journals'])
    ids={str(row['id']) for row in data['meetings']}
    for row in data['meetings']:
        expect_keys(row,MEETING_FIELDS)
        if set(row['permission_snapshot'])-member_ids:raise ValidationError('Fremder Sitzungskontext.')
        for rights in row['permission_snapshot'].values():
            if set(rights)-{'read','private','export','live','chair','protocol'}:raise ValidationError('Unzulässiges Sitzungsrecht.')
        existing=Meeting.objects.filter(pk=row['id']).first()
        # A protected live session is its own leader until controlled return.
        if existing and existing.leading_server=='protected' and existing.state in ('invited','live','finished','protocol_review','approved','return_pending') and existing.version>row['version']:
            existing.permission_snapshot=row['permission_snapshot'];existing.save(update_fields=['permission_snapshot']);continue
        upsert(Meeting,[row],MEETING_FIELDS)
        if row['leading_server']=='internal':
            from .models import SessionReturn
            SessionReturn.objects.filter(meeting_id=row['id'],state='pending').update(state='accepted')
    pending=list(data['items']);ordered=[];known=set(str(pk) for pk in AgendaItem.objects.values_list('pk',flat=True))
    while pending:
        ready=[r for r in pending if not r['parent_id'] or r['parent_id'] in known]
        if not ready:raise ValidationError('Ungültige TOP-Untergliederung.')
        for r in ready:ordered.append(r);known.add(r['id']);pending.remove(r)
    for row in ordered:
        if row['meeting_id'] not in ids:raise ValidationError('Fremder Tagesordnungspunkt.')
        existing=AgendaItem.objects.filter(pk=row['id']).select_related('meeting').first()
        if existing and existing.meeting.leading_server=='protected' and existing.meeting.state in ('invited','live','finished','protocol_review','approved','return_pending'):continue
        upsert(AgendaItem,[row],ITEM_FIELDS)
    for row in data['invitations']:
        expect_keys(row,INVITE_FIELDS)
        if row['meeting_id'] not in ids:raise ValidationError('Fremde Einladung.')
        existing=MeetingInvitation.objects.filter(pk=row['id']).first()
        if existing:
            if existing.digest!=row['digest']:raise ValidationError('Versandstand darf nicht ersetzt werden.')
        else:
            if hashlib.sha256(json.dumps(row['snapshot'],sort_keys=True).encode()).hexdigest()!=row['digest']:raise ValidationError('Falscher Versandstand.')
            fields=[x for x in INVITE_FIELDS if x!='created_at'];upsert(MeetingInvitation,[{k:v for k,v in row.items() if k!='created_at'}],fields)
    for row in data['deliveries']:
        if not MeetingInvitation.objects.filter(pk=row['invitation_id'],meeting_id__in=ids).exists():raise ValidationError('Fremder Empfängerstand.')
        upsert(InvitationDelivery,[row],DELIVERY_FIELDS)
    from .session_transfer import apply
    for journal in data['journals']:
        if journal['meeting_id'] not in ids:raise ValidationError('Fremdes Sitzungsjournal.')
        target=Meeting.objects.get(pk=journal['meeting_id'])
        if target.leading_server=='internal':apply(journal,target)
    Meeting.objects.exclude(pk__in=ids).update(permission_snapshot={})

def public_meetings(org_ids):
    rows=[]
    for obj in Meeting.objects.filter(organization_id__in=org_ids,public_enabled=True).exclude(state='preparation'):
        invitation=obj.invitations.order_by('-revision').first()
        if not invitation:continue
        data=invitation.snapshot
        titles={str(i.pk):(i.title if i.public else i.public_title) for i in obj.items.filter(removed=False)}
        text=f"{obj.public_notice}\n\nTermin: {data['starts_at']}\n\nOrt: {data['location']}\n\n## Öffentliche Tagesordnung\n\n"
        for item in data['items']:
            # Private original titles/content never enter the public record.
            title=item['title'] if item['public'] else titles.get(item['id'],'Nichtöffentliche Angelegenheit')
            text+=f"- {item['position']}. {title}\n"
        rows.append({'id':str(obj.pk),'organization_id':str(obj.organization_id),'kind':'meeting','title':data['title'],'body':text,'version':invitation.revision,'attachments':[],'metadata':{'starts_at':data['starts_at'],'ends_at':data['ends_at'],'location':data['location'],'committee_id':str(obj.committee_id)}})
    return rows

def referenced_assets(channel):
    from .models import PublicRecord
    if channel=='public':return [a for files in PublicRecord.objects.values_list('attachments',flat=True) for a in files]
    assets=[a for files in ExternalDocument.objects.values_list('attachments',flat=True) for a in files]
    for invitation in MeetingInvitation.objects.all():
        for item in invitation.snapshot['items']:
            if item.get('template'):assets+=item['template']['attachments']
    return assets
