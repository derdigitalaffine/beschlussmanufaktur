import uuid,copy,json
from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from .test_meetings import MeetingFixture
from .models import MeetingLease,MeetingEvent,OfflineReceipt,MeetingParticipant
from .live_service import claim,roster
from .offline_views import reconcile,permit
class OfflineTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db();self.device=uuid.uuid4();self.epoch=claim(self.c,self.meeting.pk,self.meeting.version,self.device)
        self.meeting.refresh_from_db();roster(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch);self.meeting.refresh_from_db()
        self.data={'batch_id':str(uuid.uuid4()),'meeting_id':str(self.meeting.pk),'user_id':str(self.clerk.pk),'context_id':str(self.c.pk),'base_version':self.meeting.version,'epoch':self.epoch,'device':str(self.device),'expires_at':(timezone.now()+timezone.timedelta(hours=48)).isoformat(),'events':[{'id':str(uuid.uuid4()),'kind':'presence','payload':{'participant_id':str(MeetingParticipant.objects.get().pk),'present':True},'occurred_at':timezone.now().isoformat()}]}
        self.data['grant']=permit(dict(self.data,version=self.data['base_version']))
    def test_expired_lease_same_epoch_reconciles_explicitly(self):
        MeetingLease.objects.update(expires_at=timezone.now()-timezone.timedelta(hours=1));v=reconcile(self.c,self.data);self.assertGreater(v,self.data['base_version']);self.assertTrue(MeetingParticipant.objects.get().present);self.assertEqual(OfflineReceipt.objects.count(),1)
        self.assertEqual(reconcile(self.c,self.data),v);self.assertEqual(MeetingEvent.objects.filter(kind='presence').count(),1)
    def test_tampered_duplicate_rejected(self):
        reconcile(self.c,self.data);self.data['events'][0]['payload']['present']=False
        with self.assertRaises(ValidationError):reconcile(self.c,self.data)
    def test_chair_takeover_conflicts(self):
        claim(self.h,self.meeting.pk,self.meeting.version,uuid.uuid4(),'Übernommen')
        with self.assertRaises(ValidationError):reconcile(self.c,self.data)
    def test_revocation_denies_all(self):
        self.c.revoked_at=timezone.now();self.c.save()
        with self.assertRaises(PermissionDenied):reconcile(self.c,self.data)
        self.assertFalse(OfflineReceipt.objects.exists())
    def test_digital_vote_not_offline(self):
        self.data['events'][0]['kind']='vote_open'
        with self.assertRaises(ValidationError):reconcile(self.c,self.data)
    def test_atomic_queue_no_partial_effect(self):
        self.data['events'].append({'id':str(uuid.uuid4()),'kind':'text','payload':{'item_id':str(uuid.uuid4()),'markdown':'Fremder TOP'},'occurred_at':timezone.now().isoformat()})
        from .models import AgendaItem
        with self.assertRaises(AgendaItem.DoesNotExist):reconcile(self.c,self.data)
        self.assertFalse(MeetingParticipant.objects.get().present);self.assertFalse(OfflineReceipt.objects.exists())
    def test_expired_prepare_rejected(self):
        self.data['expires_at']=(timezone.now()-timezone.timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValidationError):reconcile(self.c,self.data)
    def test_identity_and_preparation(self):
        identity=self.client.get('/offline/identitaet/');self.assertEqual(identity.status_code,200)
        data=self.client.post(f'/offline/sitzungen/{self.meeting.pk}/',{'hours':48}).json();self.assertFalse(data['writer']);self.assertEqual(data['roster'],[]);self.assertNotIn('password',str(data));self.assertEqual(data['context_id'],str(self.c.pk))
    def test_note_cannot_cross_account(self):
        r=self.client.post(f'/offline/notizen/{self.meeting.pk}/',json.dumps({'user_id':str(self.member.pk),'context_id':str(self.c.pk),'version':0,'markdown':'x'}),content_type='application/json');self.assertEqual(r.status_code,403)
    def test_no_session_context_denies(self):
        with self.assertRaises(PermissionDenied):reconcile(None,self.data)
    def test_future_or_naive_occurrence_rejected(self):
        self.data['events'][0]['occurred_at']='2030-01-01T00:00:00'
        with self.assertRaises(ValidationError):reconcile(self.c,self.data)
    def test_huge_note_returns_conflict(self):
        r=self.client.post(f'/offline/notizen/{self.meeting.pk}/',json.dumps({'user_id':str(self.clerk.pk),'context_id':str(self.c.pk),'version':0,'markdown':'x'*100001}),content_type='application/json');self.assertEqual(r.status_code,409)
