import uuid
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.utils import timezone
from .models import Minutes,MinutesVersion,Meeting,ItemNote,Decision,Notification,AuditEvent
from .meetings_service import meeting_access,lock_meeting

def snapshot(obj):return {'kind':obj.kind,'markdown':obj.markdown,'public_markdown':obj.public_markdown,'state':obj.state}

def archive(obj,context,reason,correction=None):
    MinutesVersion.objects.create(minutes=obj,version=obj.version,snapshot=snapshot(obj),reason=reason[:1000],actor=context.user,correction_meeting=correction)
    AuditEvent.objects.create(actor=context.user,action='minutes.'+obj.state,object_id=str(obj.pk),metadata={'version':obj.version,'reason':reason})

def generated(meeting):
    text=f'# Niederschrift · {meeting.title}\n\n{meeting.starts_at.isoformat()} · {meeting.location}\n\n## Besetzung\n\n'
    for person in meeting.roster.all():text+=f'- {person.name} · {person.function}\n'
    text+='\n## Anwesenheitsverlauf und Ausschlüsse\n\n'
    people={str(p.pk):p.name for p in meeting.roster.all()}
    for e in meeting.events.filter(kind__in=['presence','conflict','quorum']):
        p=e.payload;text+=f'- {e.occurred_at.isoformat()} · TOP {e.item.position if e.item_id else "–"} · {e.kind} · {people.get(p.get("participant_id"),"")} · {p}\n'
    for item in meeting.items.filter(removed=False):
        text+=f'\n## TOP {item.position} · {item.title} · {"öffentlich" if item.public else "nichtöffentlich"}\n\n'
        note=ItemNote.objects.filter(item=item).first()
        if note:text+=note.markdown+'\n\n'
        for motion in item.motions.all():text+=f'### Antrag · {motion.applicant}\n\n{motion.wording}\n\n'
        for d in Decision.objects.filter(vote__item=item):
            text+=f'### Beschluss {d.pk}\n\n{d.wording}\n\nErgebnis: {d.result}\n\nFeststellung: {d.chair_confirmation}\n\n'
            if d.vote.mode=='named':
                for ballot in d.vote.ballots.select_related('participant'):text+=f'- {ballot.participant.name}: {ballot.choice}\n'
    if len(text)>200000:raise ValidationError('Journal überschreitet die Niederschriftsgrenze. Vor Erstellung fachlich aufteilen; es wurde nichts gekürzt.')
    return text

@transaction.atomic
def create(context,meeting_id,meeting_version):
    meeting=lock_meeting(context,meeting_id,'protocol',meeting_version)
    if context.user_id!=meeting.scribe_id:raise PermissionDenied('Zugeordnete Schriftführung erstellt die Niederschrift.')
    if meeting.state!='finished' or Minutes.objects.filter(meeting=meeting).exists():raise ValidationError('Abgeschlossene Sitzung ohne vorhandene Niederschrift erforderlich.')
    obj=Minutes.objects.create(meeting=meeting,markdown=generated(meeting),public_markdown=f'# Öffentliche Niederschrift · {meeting.title}\n\nÖffentliche Fassung gesondert ausarbeiten und prüfen.')
    archive(obj,context,'Aus Sitzungsjournal erzeugt');meeting.state='protocol_review';meeting.version+=1;meeting.save(update_fields=['state','version']);return obj

@transaction.atomic
def change(context,minutes_id,version,action,reason='',data=None,correction_id=None):
    original=Minutes.objects.get(pk=minutes_id)
    meeting=Meeting.objects.select_for_update().get(pk=original.meeting_id)
    obj=Minutes.objects.select_for_update().get(pk=minutes_id)
    if not meeting_access(context,'protocol',meeting) or context.user_id not in (meeting.scribe_id,meeting.chair_id):raise PermissionDenied
    if meeting.leading_server!=settings.SERVER_ROLE or meeting.state=='return_pending':raise ValidationError('Niederschrift auf dem führenden Dienst bearbeiten; Rückgabe ist eingefroren.')
    if obj.version!=version:raise ValidationError('Fassung geändert; Ihren Text prüfen und erneut übernehmen.')
    correction=None;data=data or {}
    if action=='save':
        if obj.state!='draft':raise ValidationError('Geprüfte Fassung zuerst begründet zurückgeben oder berichtigen.')
        for field in ('markdown','public_markdown'):
            if not isinstance(data.get(field),str) or len(data[field])>200000:raise ValidationError('Text fehlt oder zu groß.')
            setattr(obj,field,data[field])
        if data.get('kind') not in ('result','course','verbatim'):raise ValidationError('Unbekannte Protokollart.')
        obj.kind=data['kind'];reason=reason or 'Niederschrift bearbeitet'
    elif action=='scribe_check':
        if context.user_id!=meeting.scribe_id or obj.state!='draft' or not obj.markdown.strip():raise PermissionDenied('Schriftführung prüft die eigene fertige Entwurfsfassung.')
        obj.state='scribe_checked';reason='Durch Schriftführung geprüft'
        Notification.objects.create(user=meeting.chair,text='Eine Niederschrift wartet auf Ihre Prüfung.',path=f'/sitzungen/{meeting.pk}/niederschrift/')
    elif action=='chair_check':
        if context.user_id!=meeting.chair_id or obj.state!='scribe_checked':raise PermissionDenied('Vorsitz prüft nach Schriftführung.')
        if meeting.chair_id==meeting.scribe_id:raise ValidationError('Getrennte zugeordnete Prüfer erforderlich.')
        obj.state='approved';meeting.state='approved';reason='Durch Vorsitz geprüft'
    elif action in ('return','correct'):
        if not reason.strip() or (action=='return' and obj.state!='scribe_checked') or (action=='correct' and obj.state!='approved'):raise ValidationError('Passender Prüfstand und Begründung erforderlich.')
        if action=='return' and context.user_id!=meeting.chair_id:raise PermissionDenied
        if correction_id:
            correction=Meeting.objects.filter(pk=correction_id,organization=meeting.organization,committee=meeting.committee,starts_at__gt=meeting.starts_at).first()
            if not correction:raise ValidationError('Berichtigung muss einer passenden Folgesitzung zugeordnet sein.')
        obj.state='draft';meeting.state='protocol_review'
    elif action=='publish':
        if settings.SERVER_ROLE!='internal' or not meeting_access(context,'invite',meeting) or obj.state!='approved' or not reason.strip() or not obj.public_markdown.strip():raise ValidationError('Intern genehmigte Fassung und ausdrückliche Veröffentlichungsprüfung erforderlich.')
        obj.published_version=obj.version;obj.public_snapshot={'title':'Niederschrift · '+meeting.title,'markdown':obj.public_markdown,'version':obj.version};obj.save(update_fields=['published_version','public_snapshot'])
        AuditEvent.objects.create(actor=context.user,action='minutes.published',object_id=str(obj.pk),metadata={'version':obj.version,'reason':reason});return obj
    elif action=='withdraw':
        if settings.SERVER_ROLE!='internal' or not meeting_access(context,'invite',meeting) or not reason.strip():raise PermissionDenied
        obj.published_version=None;obj.public_snapshot={};obj.save(update_fields=['published_version','public_snapshot']);AuditEvent.objects.create(actor=context.user,action='minutes.withdrawn',object_id=str(obj.pk),metadata={'reason':reason});return obj
    else:raise ValidationError('Unbekannte Niederschriftsaktion.')
    obj.version+=1;obj.save();archive(obj,context,reason,correction);meeting.version+=1;meeting.save(update_fields=['state','version']);return obj
