import time
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from core.models import Notification
from core.mail_routing import digest_origins

class Command(BaseCommand):
    help='Neutrale E-Mail-Digests aus dauerhaften Benachrichtigungen versenden.'
    def add_arguments(self,parser):parser.add_argument('--watch',action='store_true')
    def handle(self,*args,**options):
        while True:
            user_ids=list(Notification.objects.filter(emailed_at__isnull=True,read_at__isnull=True).values_list('user_id',flat=True).distinct()[:20])
            for user_id in user_ids:
                try:
                    with transaction.atomic():
                        notes=list(Notification.objects.select_for_update().select_related('user').filter(user_id=user_id,emailed_at__isnull=True,read_at__isnull=True)[:100])
                        if not notes:continue
                        user=notes[0].user
                        if user.is_active:
                            links='\n'.join(origin+'/' for origin in digest_origins(notes,user))
                            send_mail('Neue Hinweise in der Beschlussmanufaktur',f'Für Sie liegen neue Hinweise vor. Wählen Sie den passenden Arbeitsplatz und Arbeitskontext:\n{links}\n\nDiese Nachricht enthält keine vertraulichen Unterlagen.',None,[user.email])
                        Notification.objects.filter(pk__in=[n.pk for n in notes]).update(emailed_at=timezone.now())
                except Exception:self.stderr.write('Hinweisversand fehlgeschlagen. SMTP-Konfiguration prüfen.')
            if not options['watch']:break
            time.sleep(60)
