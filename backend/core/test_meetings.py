from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from .models import Organization,User,Membership,RegistryRecord,Mandate,Meeting,AgendaItem,MeetingInvitation,InvitationDelivery,MeetingAmendment,MeetingGuest
from .meetings_service import save_item,issue,approve_amendment,meeting_access,meeting_snapshot

class MeetingFixture:
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association')
        self.clerk=User.objects.create_user(username='clerk',email='clerk@example.org')
        self.chair=User.objects.create_user(username='chair',email='chair@example.org')
        self.member=User.objects.create_user(username='member',email='member@example.org')
        self.c=Membership.objects.create(organization=self.org,user=self.clerk,role='clerk')
        self.h=Membership.objects.create(organization=self.org,user=self.chair,role='chair')
        self.m=Membership.objects.create(organization=self.org,user=self.member,role='member')
        self.committee=RegistryRecord.objects.create(organization=self.org,kind='committee',name='Rat')
        self.term=RegistryRecord.objects.create(organization=self.org,kind='term',name='Periode',starts_on=timezone.localdate()-timezone.timedelta(days=365),ends_on=timezone.localdate()+timezone.timedelta(days=365))
        self.function=RegistryRecord.objects.create(organization=self.org,kind='function',name='Ratsmitglied')
        Mandate.objects.create(committee=self.committee,term=self.term,function=self.function,user=self.member,starts_on=self.term.starts_on,ends_on=self.term.ends_on)
        self.meeting=Meeting.objects.create(organization=self.org,committee=self.committee,title='Ratssitzung',starts_at=timezone.now()+timezone.timedelta(days=10),ends_at=timezone.now()+timezone.timedelta(days=10,hours=2),location='Rathaus',chair=self.chair,scribe=self.clerk,created_by=self.clerk,statutory_count=13)
        self.client.force_login(self.clerk);s=self.client.session;s['context_id']=str(self.c.pk);s.save()
    def item(self,public=True):
        obj=self.meeting;obj.refresh_from_db()
        return save_item(self.c,obj.pk,obj.version,{'title':'Öffentlicher TOP' if public else 'GEHEIMER TITEL','public_title':'' if public else 'Personalangelegenheit','position':1,'public':public})
    def invite(self):
        self.meeting.refresh_from_db();return issue(self.c,self.meeting.pk,self.meeting.version)

class MeetingTests(MeetingFixture,TestCase):
    def test_plan_pages_scoped(self):
        self.assertContains(self.client.get('/sitzungen/'),'Ratssitzung');self.assertEqual(self.client.get('/sitzungen/neu/').status_code,200)
    def test_members_do_not_read_preparation(self):self.assertFalse(meeting_access(self.m,'read',self.meeting))
    def test_invitation_fixed_and_edit_blocked(self):
        item=self.item();inv=self.invite();self.meeting.refresh_from_db()
        with self.assertRaises(ValidationError):save_item(self.c,self.meeting.pk,self.meeting.version,{'title':'Stille Änderung'},item.pk)
        self.assertEqual(inv.snapshot['items'][0]['title'],'Öffentlicher TOP')
        with self.assertRaises(ValidationError):inv.save()
    def test_members_receive_scoped_snapshot(self):
        self.item(False);self.invite();self.assertTrue(InvitationDelivery.objects.filter(user=self.member).exists())
        self.meeting.refresh_from_db();self.assertTrue(meeting_access(self.m,'private',self.meeting))
    def test_public_guest_does_not_receive_private_items(self):
        guest=User.objects.create_user(username='guest',email='guest@example.org');context=Membership.objects.create(organization=self.org,user=guest,role='member')
        MeetingGuest.objects.create(meeting=self.meeting,membership=context,expires_at=self.meeting.ends_at,private=False)
        self.item(False);self.invite();delivery=InvitationDelivery.objects.get(user=guest)
        self.assertEqual(delivery.snapshot['items'],[]);self.assertNotIn('GEHEIMER',str(delivery.snapshot))
    def test_short_notice_requires_documented_exception(self):
        self.item();self.meeting.refresh_from_db();self.meeting.starts_at=timezone.now()+timezone.timedelta(days=1);self.meeting.save()
        with self.assertRaises(ValidationError):issue(self.c,self.meeting.pk,self.meeting.version)
        self.assertEqual(issue(self.c,self.meeting.pk,self.meeting.version,'Eilbedürftig',True).revision,1)
    def test_amendment_chair_and_new_issue(self):
        self.item();first=self.invite();self.meeting.refresh_from_db()
        change=MeetingAmendment.objects.create(meeting=self.meeting,base_version=self.meeting.version,kind='urgent',reason='Dringender Bedarf',data={'title':'Neuer Gegenstand','public':True,'position':2},requested_by=self.clerk)
        with self.assertRaises(PermissionDenied):approve_amendment(self.c,change.pk,'Beschluss dokumentiert')
        approve_amendment(self.h,change.pk,'Feststellung und Beschluss geprüft');self.meeting.refresh_from_db()
        issue(self.c,self.meeting.pk,self.meeting.version,'Genehmigter Nachtrag')
        self.assertEqual(len(first.snapshot['items']),1);self.assertEqual(MeetingInvitation.objects.latest('revision').revision,2)
    def test_stale_edit_rejected(self):
        self.item()
        with self.assertRaises(ValidationError):save_item(self.c,self.meeting.pk,1,{'title':'Stale'})
    def test_expired_context_no_access(self):
        self.c.revoked_at=timezone.now();self.c.save();self.assertFalse(meeting_access(self.c,'plan',self.meeting))
    def test_parent_cycle_invalid(self):
        item=self.item();child=AgendaItem.objects.create(meeting=self.meeting,proposed_by=self.clerk,parent=item,title='Unterpunkt',position=2)
        item.parent=child
        with self.assertRaises(ValidationError):item.full_clean()
    def test_invalid_empty_form_no_server_error(self):
        self.assertEqual(self.client.post('/sitzungen/neu/',{}).status_code,200)
    def test_context_other_body_denied(self):
        other=Organization.objects.create(name='Andere',kind='union');context=Membership.objects.create(organization=other,user=self.clerk,role='clerk')
        self.assertFalse(meeting_access(context,'read',self.meeting))
