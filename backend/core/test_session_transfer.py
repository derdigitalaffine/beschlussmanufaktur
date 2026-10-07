import uuid,copy
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from .test_meetings import MeetingFixture
from .models import ExchangeState,SessionReturn,MeetingParticipant
from .live_service import claim,roster,write
from .session_transfer import bundle,validate,prepare_return,accept,apply

class SessionTransferTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db();self.meeting.authority_base=self.meeting.version;self.meeting.save();self.device=uuid.uuid4()
    def run_session(self):
        self.meeting.permission_snapshot={str(self.c.pk):['read','private','live','protocol'],str(self.h.pk):['read','private','live','protocol']};self.meeting.leading_server='protected';self.meeting.save()
        ExchangeState.objects.create(channel='protected',revision=1,received_at=timezone.now())
        with override_settings(SERVER_ROLE='protected'):
            self.epoch=claim(self.c,self.meeting.pk,self.meeting.version,self.device);self.meeting.refresh_from_db();roster(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch)
            for kind in ('begin','end'):
                self.meeting.refresh_from_db();write(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch,kind,{},uuid.uuid4())
            self.meeting.refresh_from_db();return prepare_return(self.c,self.meeting,self.meeting.version)
    def test_roundtrip_requires_explicit_acceptance(self):
        change=self.run_session();self.assertEqual(change.state,'pending');self.meeting.refresh_from_db();self.assertEqual(self.meeting.state,'return_pending')
        self.meeting.version=self.meeting.authority_base;self.meeting.state='invited';self.meeting.save()
        # Existing immutable events simulate a replayed import on the same database.
        result=accept(self.c,change.pk,'Schriftführung und Verlauf geprüft');self.assertEqual(result.leading_server,'internal');self.assertEqual(result.state,'finished')
        with self.assertRaises(ValidationError):accept(self.c,change.pk,'Nochmal')
    def test_tampered_digest_rejected(self):
        change=self.run_session();self.meeting.version=self.meeting.authority_base;self.meeting.save();SessionReturn.objects.filter(pk=change.pk).update(digest='bad')
        with self.assertRaises(ValidationError):accept(self.c,change.pk,'Geprüft')
    def test_no_implicit_merge_after_internal_change(self):
        change=self.run_session()
        with self.assertRaises(ValidationError):accept(self.c,change.pk,'Geprüft')
    def test_member_cannot_accept(self):
        change=self.run_session()
        with self.assertRaises(PermissionDenied):accept(self.m,change.pk,'Geprüft')
    def test_foreign_item_rejected(self):
        data=bundle(self.meeting);data['active_item_id']=str(uuid.uuid4())
        with self.assertRaises(ValidationError):validate(data,self.meeting)
    def test_finished_return_frozen(self):
        self.run_session();self.meeting.refresh_from_db()
        with override_settings(SERVER_ROLE='protected'):
            with self.assertRaises(ValidationError):write(self.c,self.meeting.pk,self.meeting.version,self.device,self.epoch,'text',{'item_id':str(self.meeting.items.first().pk),'markdown':'zu spät'},uuid.uuid4())
    def test_internal_journal_replica(self):
        epoch=claim(self.c,self.meeting.pk,self.meeting.version,self.device);self.meeting.refresh_from_db();roster(self.c,self.meeting.pk,self.meeting.version,self.device,epoch);self.meeting.refresh_from_db();data=bundle(self.meeting);apply(data,self.meeting);self.assertEqual(self.meeting.roster.count(),1)
    def test_integer_ids_are_local_not_transport_identity(self):
        from .models import ConflictOfInterest,Vote,Ballot
        part=MeetingParticipant.objects.create(meeting=self.meeting,user=self.member,name='Mitglied',voting=True,present=True)
        item=self.meeting.items.first();conflict=ConflictOfInterest.objects.create(participant=part,item=item,active=False,reason='aufgehoben')
        vote=Vote.objects.create(meeting=self.meeting,item=item,wording='Wortlaut',mode='named',opened_version=1,electorate=[str(part.pk)],options=['Ja','Nein','Enthaltung'])
        ballot=Ballot.objects.create(vote=vote,participant=part,choice='Ja');data=bundle(self.meeting)
        self.assertNotIn('id',data['tables']['ballots'][0]);self.assertNotIn('id',data['tables']['conflicts'][0])
        ballot.delete();conflict.delete()
        # Different host-local primary keys must not duplicate or reassign votes.
        ConflictOfInterest.objects.create(id=999,participant=part,item=item,active=False,reason='aufgehoben')
        apply(data,self.meeting);apply(data,self.meeting);self.assertEqual(Ballot.objects.count(),1);self.assertEqual(ConflictOfInterest.objects.get().pk,999)

    def test_accepted_return_is_not_polled_as_new_conflict(self):
        from unittest.mock import patch
        from .exchange import scalar
        from .session_transfer import pull_returns
        change=self.run_session();self.meeting.version=self.meeting.authority_base;self.meeting.state='invited';self.meeting.save();accept(self.c,change.pk,'Geprüft');change.refresh_from_db()
        row=scalar(change,['id','meeting_id','base_version','bundle','digest','requested_by_id','context_id'])
        with patch('core.session_transfer.transport',return_value={'returns':[row]}) as transport:
            pull_returns();transport.assert_called_once_with('protected','/transfer/sessions/')
