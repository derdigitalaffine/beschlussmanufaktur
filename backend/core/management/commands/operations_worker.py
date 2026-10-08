import time
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
class Command(BaseCommand):
    help='Interner Betriebsworker für signierte TLS-Aufträge und optionalen IMAP-Abruf.'
    def add_arguments(self,parser):parser.add_argument('--watch',action='store_true')
    def handle(self,*args,**options):
        if settings.SERVER_ROLE!='internal':raise CommandError('Nur intern ausführen.')
        while True:
            from core.tls_management import apply_pending
            from core.mail_inbox import poll
            apply_pending()
            try:poll()
            except Exception:self.stderr.write('IMAP-Abruf fehlgeschlagen; Laufzeitkonfiguration prüfen.')
            if not options['watch']:break
            time.sleep(60)
