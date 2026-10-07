from django.test import TestCase,override_settings
from django.utils import timezone
from .test_meetings import MeetingFixture
from .models import Membership,TemplateKind,Template,Consultation,AccessGrant,ExchangeState
from .meetings_service import meeting_access
from .templates_service import template_access
from .permissions import can_access
class ContextIsolationTests(MeetingFixture,TestCase):
    def setUp(self):
        super().setUp();self.item();self.invite();self.meeting.refresh_from_db()
        self.admin=Membership.objects.create(user=self.member,organization=self.org,role='organization_admin')
        kind=TemplateKind.objects.create(organization=self.org,name='Beschluss');self.t=Template.objects.create(organization=self.org,kind=kind,author=self.clerk,subject='Geschützt',classification='committee',state='ready');Consultation.objects.create(template=self.t,committee=self.committee)
    def test_mandate_does_not_union_into_administration(self):
        self.assertFalse(meeting_access(self.admin,'private',self.meeting));self.assertFalse(template_access(self.admin,'read',self.t));self.assertFalse(can_access(self.admin,'read','registry',self.committee))
        self.assertTrue(meeting_access(self.m,'private',self.meeting));self.assertTrue(template_access(self.m,'read',self.t))
    def test_chair_assignment_does_not_union_into_administration(self):
        admin=Membership.objects.create(user=self.chair,organization=self.org,role='organization_admin')
        self.assertFalse(meeting_access(admin,'chair',self.meeting));self.assertFalse(meeting_access(admin,'live',self.meeting));self.assertTrue(meeting_access(self.h,'chair',self.meeting))
    def test_scribe_assignment_does_not_union_into_author_role(self):
        author=Membership.objects.create(user=self.clerk,organization=self.org,role='author')
        self.assertFalse(meeting_access(author,'live',self.meeting));self.assertTrue(meeting_access(self.c,'live',self.meeting))
    def test_explicit_scoped_grant_still_works(self):
        AccessGrant.objects.create(organization=self.org,membership=self.admin,resource_kind='registry',resource_id=self.committee.pk,actions=['read'],reason='Gremienunterlagen ausdrücklich freigegeben')
        self.assertTrue(template_access(self.admin,'read',self.t));self.assertFalse(template_access(self.admin,'export',self.t));self.assertFalse(meeting_access(self.admin,'private',self.meeting))
    def test_legacy_external_write_snapshot_does_not_override_role(self):
        self.meeting.permission_snapshot={str(self.m.pk):['read','private','live','protocol','chair']};self.meeting.save();ExchangeState.objects.create(channel='protected',revision=1,received_at=timezone.now())
        with override_settings(SERVER_ROLE='protected'):
            self.assertTrue(meeting_access(self.m,'read',self.meeting));self.assertFalse(meeting_access(self.m,'live',self.meeting));self.assertFalse(meeting_access(self.m,'chair',self.meeting))
