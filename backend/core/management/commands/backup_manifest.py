import hashlib,json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
class Command(BaseCommand):
    help='Code-/Schema-/Austauschstand ohne Fachinhalte für eine Betriebssicherung ausgeben.'
    def handle(self,*args,**options):
        migrations={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (settings.BASE_DIR/'core/migrations').glob('*.py') if p.name!='__init__.py'}
        self.stdout.write(json.dumps({'schema':1,'role':settings.SERVER_ROLE,'code_migrations':migrations},sort_keys=True))
