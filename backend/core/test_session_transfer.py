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
