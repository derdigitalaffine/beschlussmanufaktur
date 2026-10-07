from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from .test_meetings import MeetingFixture
from .models import Vote,Decision,User,Membership
from .decision_views import update,access
class DecisionTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();item=self.item();self.invite();self.meeting.refresh_from_db();vote=Vote.objects.create(meeting=self.meeting,item=item,wording='Beschluss',mode='manual',state='confirmed',opened_version=self.meeting.version,result={'outcome':'accepted'})
        self.d=Decision.objects.create(vote=vote,wording='Straße sanieren',result=vote.result,chair_confirmation='Vorsitz festgestellt',confirmed_by=self.clerk)
        self.staff=User.objects.create_user(username='staff',email='staff@example.org');self.a=Membership.objects.create(organization=self.org,user=self.staff,role='author')
    def act(self,action,context=None,**kw):
        self.d.refresh_from_db();return update(context or self.c,self.d.pk,self.d.version,action,**kw)
    def test_assignment_progress_confirmation(self):
        self.assertFalse(access(self.a,self.d));self.act('assign',responsible=self.staff);self.d.refresh_from_db();self.assertTrue(access(self.a,self.d))
        self.act('progress',self.a,progress='Auftrag erteilt');self.act('complete',self.a,progress='Fertig')
        with self.assertRaises(PermissionDenied):self.act('close',self.a,progress='Geprüft')
        self.act('close',progress='Abnahme geprüft');self.d.refresh_from_db();self.assertEqual(self.d.status,'closed');self.assertEqual(self.d.updates.count(),4)
    def test_knowledge_no_task(self):self.act('not_required',progress='Nur Kenntnisnahme');self.d.refresh_from_db();self.assertEqual(self.d.status,'not_required')
    def test_member_cannot_edit(self):
        with self.assertRaises(PermissionDenied):self.act('progress',self.m,progress='x')
    def test_stale_progress_conflicts(self):
        old=self.d.version;self.act('assign',responsible=self.staff)
        with self.assertRaises(ValidationError):update(self.a,self.d.pk,old,'progress','Stale')
    def test_assignment_does_not_grant_other_meeting_access(self):
        self.act('assign',responsible=self.staff)
        from .meetings_service import meeting_access
        self.assertFalse(meeting_access(self.a,'private',self.meeting))
    def test_revocation_removes_task_access(self):
        self.act('assign',responsible=self.staff)
        from django.utils import timezone
        self.a.revoked_at=timezone.now();self.a.save();self.assertFalse(access(self.a,self.d))
    def test_views(self):
        self.assertContains(self.client.get('/beschluesse/'),'Straße sanieren');self.assertContains(self.client.get(f'/beschluesse/{self.d.pk}/'),'Beschlusswortlaut')
