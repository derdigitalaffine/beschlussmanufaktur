"""Trusted mailbox links; never derive workplace origins from incoming hosts."""
from urllib.parse import urlparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ExchangePolicy,TransferBatch,Meeting
from .exchange import REMOTE_ROLES
from .permissions import available_contexts
from .meetings_service import meeting_access

def workplace(context,meeting,invitation_id=None):
    if context.role not in REMOTE_ROLES or not ExchangePolicy.objects.filter(organization=meeting.organization,protected_enabled=True).exists():return settings.APPLICATION_URL
    origin=settings.EXCHANGE_PROTECTED_URL.rstrip('/');url=urlparse(origin)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.path or url.query or url.fragment or len(settings.EXCHANGE_PROTECTED_KEY)<32:raise ValidationError('Geschützter Arbeitsplatz ist noch nicht korrekt konfiguriert.')
    if invitation_id:
        latest=TransferBatch.objects.filter(channel='protected',delivered_at__isnull=False).order_by('-revision').first()
        data=latest.payload.get('data',{}) if latest and latest.delivered_at>=timezone.now()-timezone.timedelta(seconds=settings.EXCHANGE_MAX_AGE) else {}
        if not any(str(c['id'])==str(context.pk) for c in data.get('memberships',[])) or not any(str(row['id'])==str(invitation_id) for row in data.get('meeting_data',{}).get('invitations',[])):raise ValidationError('Einladungsbereitstellung extern noch nicht bestätigt; Versand wird erneut versucht.')
    return origin

def digest_origins(notes,user):
    if settings.SERVER_ROLE!='internal':return [settings.APPLICATION_URL]
    origins=set()
    for note in notes:
        parts=note.path.strip('/').split('/')
        if len(parts)>1 and parts[0]=='sitzungen':
            try:obj=Meeting.objects.filter(pk=parts[1]).first()
            except ValidationError:obj=None
            contexts=[c for c in available_contexts(user) if obj and c.organization_id==obj.organization_id and meeting_access(c,'read',obj)]
            if contexts:
                origins.add(workplace(contexts[0],obj));continue
        origins.add(settings.APPLICATION_URL)
    return sorted(origins)
