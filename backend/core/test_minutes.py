from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError,PermissionDenied
from .test_meetings import MeetingFixture
from .models import ExchangePolicy
from .minutes_service import create,change
from .exchange import snapshot
class MinutesTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db();self.meeting.state='finished';self.meeting.save();self.minutes=create(self.c,self.meeting.pk,self.meeting.version)
    def action(self,action,context=None,reason='',data=None):
        self.minutes.refresh_from_db();return change(context or self.c,self.minutes.pk,self.minutes.version,action,reason,data)
    def approve(self):self.action('scribe_check');self.action('chair_check',self.h)
    def test_order_and_separate_review(self):
        with self.assertRaises(PermissionDenied):self.action('chair_check',self.h)
        self.action('scribe_check')
        with self.assertRaises(PermissionDenied):self.action('chair_check')
        self.action('chair_check',self.h);self.minutes.refresh_from_db();self.assertEqual(self.minutes.state,'approved');self.assertEqual(self.minutes.versions.count(),3)
    def test_stale_change_preserved(self):
        old=self.minutes.version;self.action('save',data={'kind':'result','markdown':'neu','public_markdown':'öffentlich'})
        with self.assertRaises(ValidationError):change(self.c,self.minutes.pk,old,'save',data={'kind':'result','markdown':'stale','public_markdown':''})
        self.minutes.refresh_from_db();self.assertEqual(self.minutes.markdown,'neu')
    def test_member_cannot_modify(self):
        with self.assertRaises(PermissionDenied):self.action('save',self.m,data={'kind':'result','markdown':'x','public_markdown':'y'})
    def test_public_snapshot_separate_and_stable(self):
        ExchangePolicy.objects.create(organization=self.org,public_enabled=True)
        self.action('save',data={'kind':'course','markdown':'PRIVATE SECRET','public_markdown':'Freigegebene Fassung'});self.approve();self.action('publish',reason='Namen und Inhalt geprüft')
        data=snapshot('public');self.assertIn('Freigegebene Fassung',str(data));self.assertNotIn('PRIVATE SECRET',str(data))
        self.action('correct',reason='Einwendung zur Niederschrift');self.action('save',data={'kind':'course','markdown':'PRIVATE 2','public_markdown':'Ungeprüfter Entwurf'})
        self.assertNotIn('Ungeprüfter Entwurf',str(snapshot('public')))
    def test_withdraw_removes_projection(self):
        ExchangePolicy.objects.create(organization=self.org,public_enabled=True);self.approve();self.action('publish',reason='Geprüft');self.action('withdraw',reason='Berichtigung nötig');self.assertNotIn('minutes',str(snapshot('public')))
    def test_versions_immutable(self):
        v=self.minutes.versions.first()
        with self.assertRaises(ValidationError):v.save()
    def test_other_server_no_edit(self):
        with override_settings(SERVER_ROLE='protected'):
            self.meeting.permission_snapshot={str(self.c.pk):['protocol']};self.meeting.save()
            from .models import ExchangeState
            from django.utils import timezone
            ExchangeState.objects.create(channel='protected',revision=1,received_at=timezone.now())
            with self.assertRaises(ValidationError):self.action('scribe_check')
    def test_pages_and_export(self):
        self.assertContains(self.client.get(f'/sitzungen/{self.meeting.pk}/niederschrift/'),'Niederschrift')
        r=self.client.get(f'/sitzungen/{self.meeting.pk}/niederschrift/1/pdf/');self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF'))
    def test_correction_reason_archived(self):
        self.approve();self.action('correct',reason='Berichtigung beraten');self.assertEqual(self.minutes.versions.latest('version').reason,'Berichtigung beraten')

    def test_journal_minutes_replay(self):
        from .session_transfer import bundle,apply
        self.meeting.refresh_from_db();data=bundle(self.meeting);apply(data,self.meeting);apply(data,self.meeting)
        self.assertEqual(self.minutes.versions.count(),1)
