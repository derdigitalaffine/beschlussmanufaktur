from django.test import TestCase
from django.core.exceptions import PermissionDenied,ValidationError
from .models import Organization,Membership,User,PersonProfile,PersonIdentity,RegistryRecord,TemplateKind
from .identities import assign,merge,visible
from .sample_data import create,remove
class IdentitySampleTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.other=Organization.objects.create(name='Andere',kind='municipality');self.user=User.objects.create_user('admin',email='admin@example.invalid');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
    def test_testdata_cleanup_and_fachreference_block(self):
        bundle=create(self.user,self.ctx);self.assertEqual(RegistryRecord.objects.count(),3);TemplateKind.objects.create(organization=bundle.organization,name='Produktive Nutzung')
        with self.assertRaises(ValidationError):remove(self.user,self.ctx,bundle.pk)
        TemplateKind.objects.all().delete();remove(self.user,self.ctx,bundle.pk);self.assertEqual(RegistryRecord.objects.count(),0);self.assertTrue(Organization.objects.filter(pk=self.org.pk).exists());self.assertEqual(User.objects.count(),1)
    def test_samples_modified_registry_not_deleted(self):
        bundle=create(self.user,self.ctx);RegistryRecord.objects.filter(pk=bundle.record_ids[0]).update(version=2)
        with self.assertRaises(ValidationError):remove(self.user,self.ctx,bundle.pk)
    def test_identity_merge_requires_all_organization_rights(self):
        a=PersonProfile(organization=self.org,name='Anna');assign(a);a.save();b=PersonProfile(organization=self.other,name='Anna');assign(b);b.save()
        self.assertFalse(visible(self.user).filter(pk=b.identity_id).exists())
        with self.assertRaises(PermissionDenied):merge(self.user,a.identity_id,b.identity_id,'Identität geprüft')
        Membership.objects.create(user=self.user,organization=self.other,role='organization_admin');merge(self.user,a.identity_id,b.identity_id,'Identität geprüft');a.refresh_from_db();self.assertEqual(a.identity_id,b.identity_id);self.assertEqual(PersonIdentity.objects.count(),1)
    def test_central_account_reused_without_shared_public_fields(self):
        a=PersonProfile(organization=self.org,name='Admin',user=self.user,public_fields=['name']);assign(a);a.save();b=PersonProfile(organization=self.other,name='Admin',user=self.user);assign(b);b.save();self.assertEqual(a.identity_id,b.identity_id);self.assertEqual(b.public_fields,[])
