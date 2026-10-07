from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core import mail
from django.utils import timezone
from .test_meetings import MeetingFixture
from .models import ExchangePolicy,TransferBatch,InvitationDelivery,Notification
from .exchange import snapshot
from .mail_routing import workplace
@override_settings(EXCHANGE_PROTECTED_URL='https://gremien.example.org',EXCHANGE_PROTECTED_KEY='k'*32,APPLICATION_URL='https://ris.intern.example.org')
class MailRoutingTests(MeetingFixture,TestCase):
    def setUp(self):super().setUp();self.item();self.inv=self.invite();self.meeting.refresh_from_db();ExchangePolicy.objects.create(organization=self.org,protected_enabled=True)
    def test_invitation_waits_for_external_materials(self):
        call_command('invitation_worker');self.assertFalse(mail.outbox);self.assertFalse(InvitationDelivery.objects.filter(delivered_at__isnull=False).exists())
        TransferBatch.objects.create(channel='protected',revision=1,payload={'data':snapshot('protected')},delivered_at=timezone.now())
        call_command('invitation_worker');self.assertTrue(mail.outbox);self.assertTrue(all('https://gremien.example.org/' in m.body for m in mail.outbox));self.assertTrue(all('https://ris.intern.example.org' not in m.body for m in mail.outbox))
    def test_invalid_origin_never_sends_link(self):
        with override_settings(EXCHANGE_PROTECTED_URL='https://evil.example.org/path'):
            with self.assertRaises(ValidationError):workplace(self.m,self.meeting)
    def test_protected_review_notification_uses_protected_origin(self):
        Notification.objects.all().delete();Notification.objects.create(user=self.chair,text='Niederschrift wartet auf Prüfung.',path=f'/sitzungen/{self.meeting.pk}/niederschrift/')
        with override_settings(SERVER_ROLE='protected',APPLICATION_URL='https://gremien.example.org'):
            call_command('notification_worker')
        self.assertEqual(len(mail.outbox),1);self.assertIn('https://gremien.example.org/',mail.outbox[0].body);self.assertNotIn('Niederschrift wartet',mail.outbox[0].body)
    def test_default_single_server_link_unchanged(self):
        ExchangePolicy.objects.update(protected_enabled=False);self.assertEqual(workplace(self.m,self.meeting),'https://ris.intern.example.org')
