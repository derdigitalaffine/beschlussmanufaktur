from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from .test_meetings import MeetingFixture
from .models import PersonalNote,Membership,WorkspaceEntry,User
from .member_views import save_note,resources
class MemberTests(MeetingFixture,TestCase):
    def setUp(self):super().setUp();self.item();self.invite();self.meeting.refresh_from_db()
    def test_notes_only_owner_context(self):
        save_note(self.m,self.meeting.pk,0,'PRIVATNOTIZ');self.assertEqual(PersonalNote.objects.get().owner_id,self.member.pk)
        r=self.client.get(f'/sitzungen/{self.meeting.pk}/notiz/');self.assertNotContains(r,'PRIVATNOTIZ')
        self.assertNotIn('PRIVATNOTIZ',str(resources(self.c)))
        from .session_transfer import bundle
        self.assertNotIn('PRIVATNOTIZ',str(bundle(self.meeting)))
    def test_note_stale_version(self):
        save_note(self.m,self.meeting.pk,0,'erste')
        with self.assertRaises(ValidationError):save_note(self.m,self.meeting.pk,0,'alte')
        self.assertEqual(PersonalNote.objects.get().markdown,'erste')
    def test_revocation_denies_note(self):
        from django.utils import timezone
        self.m.revoked_at=timezone.now();self.m.save()
        with self.assertRaises(PermissionDenied):save_note(self.m,self.meeting.pk,0,'privat')
    def test_new_context_has_separate_note(self):
        save_note(self.m,self.meeting.pk,0,'Ratsmitglied');other=Membership.objects.create(user=self.member,organization=self.org,role='reviewer');save_note(other,self.meeting.pk,0,'Andere Rolle');self.assertEqual(PersonalNote.objects.count(),2)
    def test_favorites_scoped_and_revoked_hidden(self):
        self.client.force_login(self.member);s=self.client.session;s['context_id']=str(self.m.pk);s.save()
        self.assertEqual(self.client.post('/mein-bereich/',{'kind':'meeting','resource_id':str(self.meeting.pk)}).status_code,302);self.assertEqual(WorkspaceEntry.objects.get().owner_id,self.member.pk)
        self.assertContains(self.client.get('/mein-bereich/'),'Ratssitzung')
    def test_wrong_body_no_search_result(self):
        from .models import Organization
        org=Organization.objects.create(name='Andere',kind='union');c=Membership.objects.create(user=self.clerk,organization=org,role='clerk');self.assertEqual(resources(c),[])
    def test_never_authorized_favorite(self):self.assertEqual(self.client.post('/mein-bereich/',{'kind':'meeting','resource_id':'00000000-0000-0000-0000-000000000000'}).status_code,403)
    def test_note_xss_escaped(self):
        self.client.post(f'/sitzungen/{self.meeting.pk}/notiz/',{'version':0,'markdown':'<script>alert(1)</script>'})
        r=self.client.get(f'/sitzungen/{self.meeting.pk}/notiz/');self.assertNotContains(r,'<script>alert(1)</script>')
