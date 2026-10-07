from django.test import override_settings
from .test_meetings import MeetingTests
from .models import ExchangePolicy,ExchangeState,Meeting,MeetingInvitation,InvitationDelivery
from .exchange import snapshot,receive
from .meetings_service import meeting_access

@override_settings(EXCHANGE_SOURCE='b1d0ec0f-857c-452b-bc65-02ea198a2c4c')
class MeetingTransferTests(MeetingTests):
    def setUp(self):
        super().setUp();ExchangePolicy.objects.create(organization=self.org,protected_enabled=True,public_enabled=True)
        for user in (self.clerk,self.chair,self.member):user.exchange_managed=True;user.save()
    def test_protected_roundtrip_invitation_and_contexts(self):
        self.item();inv=self.invite();data=snapshot('protected')
        payload={'schema':1,'source':'b1d0ec0f-857c-452b-bc65-02ea198a2c4c','channel':'protected','revision':1,'data':data}
        InvitationDelivery.objects.all().delete();MeetingInvitation.objects.all().delete()
        receive(payload,'protected');receive(dict(payload,revision=2),'protected')
        self.assertEqual(MeetingInvitation.objects.get(pk=inv.pk).digest,inv.digest)
        self.meeting.refresh_from_db()
        with override_settings(SERVER_ROLE='protected'):
            self.assertTrue(meeting_access(self.m,'read',self.meeting));self.assertFalse(meeting_access(self.c,'plan',self.meeting));self.assertTrue(meeting_access(self.c,'live',self.meeting))
    def test_public_notice_has_no_private_original_title(self):
        self.item(False);self.invite();self.meeting.refresh_from_db();self.meeting.public_enabled=True;self.meeting.save()
        data=snapshot('public');text=str(data)
        self.assertIn('Personalangelegenheit',text);self.assertNotIn('GEHEIMER TITEL',text)
    def test_no_accounts_for_public_meeting(self):
        self.item();self.invite();self.meeting.refresh_from_db();self.meeting.public_enabled=True;self.meeting.save()
        self.assertNotIn('password',str(snapshot('public')));self.assertNotIn('clerk@example.org',str(snapshot('public')))
