import time
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from core.exchange import queue_snapshot,deliver,pull_events
from core.models import TransferBatch

class Command(BaseCommand):
    help='Interner Transferworker. Externe Dienste öffnen keine Verbindung nach innen.'
    def add_arguments(self,parser):
        parser.add_argument('--watch',action='store_true')
        parser.add_argument('--snapshot',action='store_true')
    def handle(self,*args,**options):
        if settings.SERVER_ROLE!='internal':raise CommandError('Nur intern ausführen.')
        while True:
            for channel in ('protected','public'):
                if not getattr(settings,'EXCHANGE_'+channel.upper()+'_KEY') or not getattr(settings,'EXCHANGE_'+channel.upper()+'_URL'):continue
                if options['snapshot'] or options['watch']:
                    # Periodic snapshots propagate revocation/expiry even without a UI action.
                    queue_snapshot(channel)
                for batch in TransferBatch.objects.filter(channel=channel,delivered_at__isnull=True).order_by('revision'):
                    if not deliver(batch):break
            if settings.EXCHANGE_PROTECTED_URL and settings.EXCHANGE_PROTECTED_KEY:
                try:
                    pull_events()
                    from core.session_transfer import pull_returns
                    pull_returns()
                except Exception:self.stderr.write('Abholung fehlgeschlagen. Verbindung und Konfiguration prüfen.')
            if not options['watch']:break
            time.sleep(60)
