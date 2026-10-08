from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Organization,MailReceipt
from .mail_inbox import ingest,MAX_BYTES
class MailInboxTests(TestCase):
    def test_uid_validity_idempotence_and_safe_text(self):
        org=Organization.objects.create(name='VG',kind='association')
        raw=b'From: sender@example.org\r\nSubject: Report\r\nContent-Type: text/plain\r\n\r\n<script>alert(1)</script>'
        obj=ingest(org,'mailbox',1,5,raw);self.assertEqual(obj.category,'unassigned');self.assertIn('<script>',obj.preview)
        self.assertEqual(ingest(org,'mailbox',1,5,raw).pk,obj.pk);ingest(org,'mailbox',2,5,raw);self.assertEqual(MailReceipt.objects.count(),2)
        with self.assertRaises(ValidationError):ingest(org,'mailbox',1,6,b'a'*(MAX_BYTES+1))
        self.assertEqual(ingest(org,'mailbox',1,6,b'',oversized=True).preview,'')
