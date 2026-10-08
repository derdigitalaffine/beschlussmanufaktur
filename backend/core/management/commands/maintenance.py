from django.core.management.base import BaseCommand
from core.maintenance import gate,enabled
from core.models import OperationalState,AuditEvent
class Command(BaseCommand):
    help='Lokaler Betreiber friert Schreibanfragen konsistent ein; bestehende Änderungen abschließen lassen.'
    def add_arguments(self,parser):parser.add_argument('operation',choices=['on','off','status']);parser.add_argument('--reason',default='Lokale Betriebssicherung')
    def handle(self,*args,**options):
        with gate(exclusive=True):
            if options['operation']=='on':OperationalState.objects.update_or_create(key='maintenance',defaults={'value':{'reason':options['reason'][:500]}})
            elif options['operation']=='off':OperationalState.objects.filter(key='maintenance').delete()
            if options['operation']!='status':AuditEvent.objects.create(action='maintenance.'+options['operation'],metadata={'reason':options['reason'][:500]})
            self.stdout.write('on' if enabled() else 'off')
