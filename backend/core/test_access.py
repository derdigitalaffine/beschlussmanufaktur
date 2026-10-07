from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Organization,User,Membership,RegistryRecord,AccessGrant
from .permissions import can_access

class AccessTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.other=Organization.objects.create(name='Andere',kind='union')
        self.user=User.objects.create_user(username='person',email='person@example.org',is_superuser=True)
        self.context=Membership.objects.create(user=self.user,organization=self.org,role='member')
        self.record=RegistryRecord.objects.create(organization=self.org,kind='committee',name='Rat')
    def test_default_deny_superuser(self):self.assertFalse(can_access(self.context,'read','registry',self.record))
    def test_grant_scoped_and_revocable(self):
        grant=AccessGrant.objects.create(organization=self.org,membership=self.context,resource_kind='registry',resource_id=self.record.pk,actions=['read'],reason='Beratung')
        self.assertTrue(can_access(self.context,'read','registry',self.record));self.assertFalse(can_access(self.context,'edit','registry',self.record))
        grant.revoked_at=timezone.now();grant.save();self.assertFalse(can_access(self.context,'read','registry',self.record))
    def test_foreign_grant_rejected(self):
        grant=AccessGrant(organization=self.other,membership=self.context,resource_kind='organization',resource_id=self.other.pk,actions=['read'],reason='Test')
        with self.assertRaises(ValidationError):grant.full_clean()
    def test_expired_context_overrides_grant(self):
        AccessGrant.objects.create(organization=self.org,membership=self.context,resource_kind='organization',resource_id=self.org.pk,actions=['read'],reason='Test')
        self.context.revoked_at=timezone.now();self.context.save();self.assertFalse(can_access(self.context,'read','registry',self.record))
    def test_foreign_resource_id_rejected(self):
        foreign=RegistryRecord.objects.create(organization=self.other,kind='committee',name='Fremd')
        grant=AccessGrant(organization=self.org,membership=self.context,resource_kind='registry',resource_id=foreign.pk,actions=['read'],reason='Test')
        with self.assertRaises(ValidationError):grant.full_clean()
