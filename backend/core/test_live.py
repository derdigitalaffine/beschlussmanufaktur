import uuid
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from .test_meetings import MeetingFixture
from .models import MeetingEvent,MeetingLease,MeetingParticipant,ConflictOfInterest,ItemNote,MeetingGuest,User,Membership
from .live_service import claim,roster,write,quorum

class LiveTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db();self.device=uuid.uuid4()
        self.epoch=claim(self.c,self.meeting.pk,self.meeting.version,self.device)
        self.meeting.refresh_from_db();roster(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch);self.meeting.refresh_from_db()
    def send(self,kind,data,event_id=None):
        self.meeting.refresh_from_db();event=write(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch,kind,data,event_id or uuid.uuid4());self.meeting.refresh_from_db();return event
    def test_presence_and_top_reference(self):
        person=MeetingParticipant.objects.get(user=self.member);self.send('presence',{'participant_id':str(person.pk),'present':True})
        person.refresh_from_db();self.assertTrue(person.present);self.assertEqual(quorum(self.meeting)['present'],1)
    def test_conflict_separate_from_attendance(self):
        person=MeetingParticipant.objects.get(user=self.member);self.send('presence',{'participant_id':str(person.pk),'present':True});item=self.meeting.items.first()
        self.send('conflict',{'participant_id':str(person.pk),'item_id':str(item.pk),'active':True,'reason':'Vorsitz festgestellt'})
        person.refresh_from_db();self.assertTrue(person.present);self.assertEqual(quorum(self.meeting,item)['present'],0)
    def test_duplicate_event_is_idempotent(self):
        person=MeetingParticipant.objects.get(user=self.member);data={'participant_id':str(person.pk),'present':True};identifier=uuid.uuid4()
        first=self.send('presence',data,identifier);version=self.meeting.version
        again=self.send('presence',data,identifier);self.assertEqual(first.pk,again.pk);self.assertEqual(self.meeting.version,version)
    def test_event_id_cannot_change_content(self):
        person=MeetingParticipant.objects.get(user=self.member);identifier=uuid.uuid4();self.send('presence',{'participant_id':str(person.pk),'present':True},identifier)
        with self.assertRaises(ValidationError):self.send('presence',{'participant_id':str(person.pk),'present':False},identifier)
    def test_chair_takeover_invalidates_old_writer(self):
        self.meeting.refresh_from_db();chair_device=uuid.uuid4()
        with self.assertRaises(ValidationError):claim(self.h,self.meeting.pk,self.meeting.version,chair_device)
        claim(self.h,self.meeting.pk,self.meeting.version,chair_device,'Schriftführung übernimmt Vorsitz')
        with self.assertRaises(ValidationError):self.send('begin',{})
    def test_member_cannot_self_register_attendance(self):
        person=MeetingParticipant.objects.get(user=self.member)
        with self.assertRaises(PermissionDenied):write(self.m,self.meeting.pk,self.meeting.version,self.device,self.epoch,'presence',{'participant_id':str(person.pk),'present':True},uuid.uuid4())
    def test_expired_lease_denies_write(self):
        MeetingLease.objects.update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
        with self.assertRaises(ValidationError):self.send('begin',{})
    def test_no_two_server_writers(self):
        with override_settings(SERVER_ROLE='protected'):
            with self.assertRaises(PermissionDenied):self.send('begin',{})
    def test_live_end_disallows_further_text(self):
        self.send('begin',{});self.send('end',{})
        with self.assertRaises(ValidationError):self.send('text',{'item_id':str(self.meeting.items.first().pk),'markdown':'Zu spät'})
    def test_quorum_event_repeated(self):
        item=self.meeting.items.first();identifier=uuid.uuid4();data={'item_id':str(item.pk),'confirmed':False,'reason':'Zu wenige anwesend'}
        self.send('quorum',dict(data),identifier);self.send('quorum',dict(data),identifier)
        self.assertEqual(MeetingEvent.objects.filter(pk=identifier).count(),1)
    def test_workspace_render(self):
        r=self.client.get(f'/sitzungen/{self.meeting.pk}/live/');self.assertEqual(r.status_code,200);self.assertContains(r,'Sitzungshoheit')
    def test_public_guest_no_private_top_or_roster(self):
        guest=User.objects.create_user(username='guest2',email='guest2@example.org');member=Membership.objects.create(organization=self.org,user=guest,role='member')
        MeetingGuest.objects.create(meeting=self.meeting,membership=member,expires_at=self.meeting.ends_at,private=False)
        item=self.meeting.items.first();item.public=False;item.public_title='Nichtöffentlich';item.title='PRIVATE GEHEIM';item.save();self.meeting.active_item=item;self.meeting.save()
        self.client.force_login(guest);s=self.client.session;s['context_id']=str(member.pk);s.save();r=self.client.get(f'/sitzungen/{self.meeting.pk}/live/')
        self.assertNotContains(r,'PRIVATE GEHEIM');self.assertNotContains(r,'Ratsmitglied')
