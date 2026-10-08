from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from .models import OperationalState
class MaintenanceTests(TestCase):
    def test_writes_blocked_reads_preserved_and_flag_explicit(self):
        call_command('maintenance','on',stdout=StringIO())
        self.assertEqual(self.client.get('/health/ready/').status_code,200);self.assertEqual(self.client.post('/anmelden/',{}).status_code,503);self.assertEqual(self.client.post('/abmelden/',{}).status_code,503)
        call_command('maintenance','off',stdout=StringIO());self.assertEqual(self.client.post('/anmelden/',{}).status_code,200)
    def test_code_manifest_no_private_rows(self):
        out=StringIO();call_command('backup_manifest',stdout=out);self.assertIn('code_migrations',out.getvalue());self.assertNotIn('password',out.getvalue())
