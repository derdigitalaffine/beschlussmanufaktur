from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import PermissionDenied,ValidationError
from .models import User,Organization,Membership,SystemOperator,EmergencyAccess,Template,TemplateKind
from .emergency import approve
from .templates_service import template_access
from .permissions import available_contexts
class EmergencyTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.op=User.objects.create_user('operator',email='op@example.invalid');self.admin=User.objects.create_user('admin',email='admin@example.invalid');self.ctx=Membership.objects.create(user=self.admin,organization=self.org,role='organization_admin');SystemOperator.objects.create(user=self.op)
        kind=TemplateKind.objects.create(organization=self.org,name='Beschluss');self.target=Template.objects.create(organization=self.org,kind=kind,author=self.admin,subject='Ziel');self.other=Template.objects.create(organization=self.org,kind=kind,author=self.admin,subject='Anderes')
        self.req=EmergencyAccess.objects.create(operator=self.op,organization=self.org,resource_kind='template',resource_id=self.target.pk,reason='Störung gezielt prüfen',expires_at=timezone.now()+timedelta(minutes=30))
    def test_approval_exact_read_scope_expiry_and_operator_revocation(self):
        obj=approve(self.ctx,self.req.pk,True);c=obj.membership;self.assertEqual(c.role,'emergency');self.assertTrue(template_access(c,'read',self.target));self.assertFalse(template_access(c,'edit',self.target));self.assertFalse(template_access(c,'read',self.other));SystemOperator.objects.filter(user=self.op).update(enabled=False);self.assertFalse(available_contexts(self.op).exists())
    def test_no_self_approval_and_no_technical_implicit_rights(self):
        self.req.operator=self.admin;self.req.save();SystemOperator.objects.create(user=self.admin)
        with self.assertRaises(PermissionDenied):approve(self.ctx,self.req.pk,True)
        self.assertFalse(template_access(self.ctx,'read',self.target))
