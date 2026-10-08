import time
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import InvitationDelivery,Membership
from core.permissions import available_contexts
from core.meetings_service import meeting_access
from core.invitation_packets import calendar
from core.mail_routing import workplace

class Command(BaseCommand):
    help='Fixierte Sitzungseinladungen per SMTP versenden; neutraler Link und Kalenderdatei.'
    def add_arguments(self,parser):parser.add_argument('--watch',action='store_true')
    def handle(self,*args,**options):
        while True:
            from core.account_mail import send_pending
            send_pending()
            deliveries=InvitationDelivery.objects.filter(delivered_at__isnull=True).select_related('invitation__meeting','user').order_by('invitation__created_at')[:50]
            for delivery in deliveries:
                delivery.attempts+=1;delivery.save(update_fields=['attempts'])
                context=available_contexts(delivery.user).filter(pk=delivery.snapshot['context_id']).first()
                if not context or not meeting_access(context,'read',delivery.invitation.meeting):
                    delivery.error='Zugriff nicht mehr gültig; kein Versand.';delivery.save(update_fields=['error']);continue
                try:
                    origin=workplace(context,delivery.invitation.meeting,delivery.invitation_id)
                    message=EmailMessage('Sitzungseinladung / Nachtrag verfügbar',f'Eine Sitzungseinladung oder ein Nachtrag liegt für Sie bereit. Öffnen Sie den Arbeitsplatz und wählen Sie den zugehörigen Kontext: {origin}/\n\nDie Unterlagen werden nur nach Anmeldung bereitgestellt. Diese Nachricht enthält keine vertraulichen Tagesordnungspunkte.',settings.DEFAULT_FROM_EMAIL,[delivery.user.email])
                    # Calendar is limited to meeting metadata, never private agenda/document content.
                    message.attach('sitzung.ics',calendar(delivery.snapshot),'text/calendar');message.send()
                except ValidationError:delivery.error='Bereitstellung oder Arbeitsplatzkonfiguration noch nicht bestätigt; erneuter Versuch.'
                except Exception:delivery.error='SMTP-Versand fehlgeschlagen; Wiederholung ausstehend.'
                else:delivery.delivered_at=timezone.now();delivery.error=''
                delivery.save(update_fields=['delivered_at','error'])
            if not options['watch']:break
            time.sleep(60)
