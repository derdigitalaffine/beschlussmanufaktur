import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from .test_meetings import MeetingFixture
from .models import MeetingParticipant,Vote,Ballot,Decision
from .live_service import claim,roster,write
from .voting import open_vote,cast,finish,confirm

class VoteTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db();self.device=uuid.uuid4();self.epoch=claim(self.c,self.meeting.pk,self.meeting.version,self.device)
        self.meeting.refresh_from_db();roster(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch)
        self.send('presence',{'participant_id':str(MeetingParticipant.objects.get(user=self.member).pk),'present':True});self.send('begin',{});self.send('top',{'item_id':str(self.meeting.items.first().pk)})
        self.send('quorum',{'item_id':str(self.meeting.items.first().pk),'confirmed':True,'reason':'Sondervoraussetzungen vom Vorsitz festgestellt'})
    def send(self,kind,data):
        self.meeting.refresh_from_db();return write(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch,kind,data,uuid.uuid4())
    def open(self,mode='named',rule='majority_cast',options=None):
        self.meeting.refresh_from_db();return open_vote(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch,'Beschluss',mode,rule,options or ['Ja','Nein','Enthaltung'])
    def close(self,vote,counts=None):
        self.meeting.refresh_from_db();return finish(self.c,vote.pk,self.meeting.version,self.device,self.epoch,counts)
    def test_named_vote_duplicate_and_decision(self):
        v=self.open();identifier=uuid.uuid4();cast(self.m,v.pk,'Ja',identifier);cast(self.m,v.pk,'Ja',identifier);self.assertEqual(Ballot.objects.count(),1)
        with self.assertRaises(ValidationError):cast(self.m,v.pk,'Nein',uuid.uuid4())
        self.close(v);self.meeting.refresh_from_db();d=confirm(self.c,v.pk,self.meeting.version,self.device,self.epoch,'Angenommen','Vorsitz hat Ergebnis festgestellt');self.assertEqual(d.result['outcome'],'accepted')
    def test_wrong_context_no_vote(self):
        v=self.open()
        with self.assertRaises(PermissionDenied):cast(self.c,v.pk,'Ja',uuid.uuid4())
    def test_presence_change_aborts(self):
        v=self.open();self.send('presence',{'participant_id':str(MeetingParticipant.objects.get(user=self.member).pk),'present':False});v.refresh_from_db();self.assertEqual(v.state,'aborted')
        with self.assertRaises(ValidationError):cast(self.m,v.pk,'Ja',uuid.uuid4())
    def test_quorum_must_be_current(self):
        self.send('presence',{'participant_id':str(MeetingParticipant.objects.get(user=self.member).pk),'present':True})
        with self.assertRaises(ValidationError):self.open()
    def test_missing_not_abstention(self):
        v=self.close(self.open());self.assertEqual(v.result['missing'],1);self.assertEqual(v.result['counts'],{});self.assertEqual(v.result['outcome'],'rejected')
    def test_secret_paper_has_no_identity_ballots(self):
        v=self.close(self.open('secret'),{'Ja':1,'Nein':0,'Enthaltung':0});self.assertEqual(v.result['counts']['Ja'],1);self.assertFalse(Ballot.objects.exists())
    def test_manual_overcount_rejected(self):
        v=self.open('manual')
        with self.assertRaises(ValidationError):self.close(v,{'Ja':2,'Nein':0,'Enthaltung':0})
    def test_election_needs_chair_determination(self):
        v=self.close(self.open('manual','election',['A','B']),{'A':1,'B':0});self.assertEqual(v.result['outcome'],'chair_determination_required')
    def test_view(self):self.assertContains(self.client.get(f'/sitzungen/{self.meeting.pk}/abstimmungen/'),'Abstimmungen')
