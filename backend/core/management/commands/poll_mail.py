from django.core.management.base import BaseCommand,CommandError
from core.mail_inbox import poll
class Command(BaseCommand):
    help='Konfigurierten IMAP-Ordner über TLS in den internen Prüfposteingang übernehmen.'
    def handle(self,*args,**options):
        try:count=poll()
        except Exception:raise CommandError('IMAP-Abruf fehlgeschlagen. Konfiguration/Erreichbarkeit prüfen; keine Zugangsdaten protokolliert.') from None
        self.stdout.write(str(count)+' Eingänge verarbeitet.')
