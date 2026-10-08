from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from core.models import User,SystemOperator,AuditEvent
class Command(BaseCommand):
    help='Lokaler Betreiber weist eine technische Betriebsrolle ausdrücklich zu/entzieht sie; keine Fachrechte.'
    def add_arguments(self,parser):parser.add_argument('email');parser.add_argument('--revoke',action='store_true')
    def handle(self,*args,**options):
        if settings.SERVER_ROLE!='internal':raise CommandError('Nur auf dem internen Dienst.')
        try:user=User.objects.get(email=options['email'].lower(),is_active=True)
        except User.DoesNotExist:raise CommandError('Aktives Konto nicht vorhanden.')
        SystemOperator.objects.update_or_create(user=user,defaults={'enabled':not options['revoke']});AuditEvent.objects.create(actor=user,action='operator.local_assignment',metadata={'enabled':not options['revoke']});self.stdout.write('Technische Betriebsrolle aktualisiert; Fachrechte unverändert.')
