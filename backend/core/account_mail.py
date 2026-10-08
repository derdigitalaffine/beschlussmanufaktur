from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import InvitationDispatch,AuditEvent
from .invitations import inviter_authorized
from .secret_store import decrypt

def send_pending():
    if settings.SERVER_ROLE!='internal':return 0
    count=0
    for identifier in InvitationDispatch.objects.filter(delivered_at__isnull=True,attempts__lt=10).values_list('pk',flat=True)[:50]:
        with transaction.atomic():
            obj=InvitationDispatch.objects.select_for_update().select_related('invitation').get(pk=identifier)
            if obj.delivered_at:continue
            invitation=obj.invitation
            if invitation.revoked_at or invitation.accepted_at or invitation.expires_at<=timezone.now() or not inviter_authorized(invitation):
                obj.encrypted_token='';obj.last_error='Einladung nicht mehr gültig.';obj.attempts=10;obj.save();continue
            obj.attempts+=1
            try:
                token=decrypt(obj.encrypted_token);link=settings.APPLICATION_URL+'/einladung/#'+token
                send_mail('Einladung zur Beschlussmanufaktur','Für Sie liegt eine persönliche Einladung vor: '+link+'\n\nEinladungscode: '+token+'\n\nGültigkeit: sieben Tage. Bestehendes Konto anmelden; neues Konto richtet sein Passwort selbst ein.',None,[invitation.email])
            except Exception:obj.last_error='Versand fehlgeschlagen; Konfiguration und Warteschlange prüfen.'
            else:
                obj.delivered_at=timezone.now();obj.encrypted_token='';obj.last_error='';count+=1
                AuditEvent.objects.create(actor=invitation.invited_by,action='invitation.sent',object_id=str(invitation.pk),metadata={'organization':str(invitation.organization_id),'queued':True})
            obj.save()
    return count
