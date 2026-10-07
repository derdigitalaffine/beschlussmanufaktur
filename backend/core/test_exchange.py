import json,uuid
from django.test import TestCase,RequestFactory,override_settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from .models import Organization,RegistryRecord,User,Membership,ExchangePolicy,ExchangeState,PublicRecord,RemoteChange,AccessGrant
from .exchange import signed_headers,authorize,snapshot,receive,queue_snapshot
from .permissions import available_contexts

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'],EXCHANGE_SOURCE='b1d0ec0f-857c-452b-bc65-02ea198a2c4c',EXCHANGE_PROTECTED_KEY='p'*40,EXCHANGE_PUBLIC_KEY='u'*40)
class ExchangeTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association')
        self.user=User.objects.create_user(username='person',email='person@example.org',password='long-Test-password-789')
        self.context=Membership.objects.create(user=self.user,organization=self.org,role='member')
        self.record=RegistryRecord.objects.create(organization=self.org,kind='committee',name='Rat',details='VERTRAULICH')
        ExchangePolicy.objects.create(organization=self.org,protected_enabled=True,public_enabled=True)
    def request(self,body=b'{}',channel='protected'):
        h=signed_headers(channel,'POST','/transfer/inbox/',body)
        return RequestFactory().post('/transfer/inbox/',data=body,content_type='application/json',**{'HTTP_'+k.upper().replace('-','_'):v for k,v in h.items() if k.startswith('X-')})
    def payload(self,channel,data,revision=1):
        from django.conf import settings
        return {'schema':1,'source':settings.EXCHANGE_SOURCE,'channel':channel,'revision':revision,'data':data}
    def test_signatures_and_replay(self):
        req=self.request();authorize(req,'protected')
        with self.assertRaises(PermissionDenied):authorize(req,'protected')
    def test_different_channel_key(self):
        with self.assertRaises(PermissionDenied):authorize(self.request(channel='public'),'protected')
    def test_tampered_body(self):
        req=self.request();req._body=b'{"tampered":1}'
        with self.assertRaises(PermissionDenied):authorize(req,'protected')
    def test_public_positive_list(self):
        data=snapshot('public');text=json.dumps(data)
        for secret in ['VERTRAULICH','password','person@example.org']:self.assertNotIn(secret,text)
        receive(self.payload('public',data),'public')
        self.assertEqual(PublicRecord.objects.count(),2)
    def test_public_reject_private_fields(self):
        data=snapshot('public');data['users']=[]
        with self.assertRaises(ValidationError):receive(self.payload('public',data),'public')
        self.assertFalse(PublicRecord.objects.exists())
    def test_no_opt_in_no_export(self):
        ExchangePolicy.objects.all().delete();self.assertEqual(snapshot('public'),{'records':[]});self.assertEqual(snapshot('protected')['users'],[])
    def test_internal_admin_not_transferred(self):
        self.context.role='organization_admin';self.context.save();self.assertEqual(snapshot('protected')['users'],[])
    def test_wrong_source_stale_revision(self):
        payload=self.payload('public',snapshot('public'),2);receive(payload,'public')
        with self.assertRaises(ValidationError):receive(self.payload('public',snapshot('public'),1),'public')
        payload['source']=str(uuid.uuid4())
        with self.assertRaises(ValidationError):receive(payload,'public')
    def test_withdrawal_and_idempotence(self):
        payload=self.payload('public',snapshot('public'));receive(payload,'public');receive(payload,'public');self.assertEqual(PublicRecord.objects.count(),2)
        receive(self.payload('public',{'records':[]},2),'public');self.assertFalse(PublicRecord.objects.exists())
    @override_settings(SERVER_ROLE='protected')
    def test_external_permission_expires_when_sync_stale(self):
        self.assertFalse(available_contexts(self.user).exists())
        ExchangeState.objects.create(channel='protected',received_at=timezone.now(),revision=1)
        self.assertTrue(available_contexts(self.user).exists())
        ExchangeState.objects.update(received_at=timezone.now()-timezone.timedelta(days=2))
        self.assertFalse(available_contexts(self.user).exists())
    def test_protected_roundtrip_requires_dedicated_accounts(self):
        data=snapshot('protected')
        with self.assertRaises(ValidationError):receive(self.payload('protected',data),'protected')
        self.user.exchange_managed=True;self.user.save()
        receive(self.payload('protected',data),'protected')
        self.user.refresh_from_db();self.assertFalse(self.user.is_superuser);self.assertTrue(self.user.check_password('long-Test-password-789'))
    def test_revoke_transfers_to_existing_replica(self):
        self.user.exchange_managed=True;self.user.save()
        receive(self.payload('protected',snapshot('protected')),'protected')
        self.context.revoked_at=timezone.now();self.context.save()
        receive(self.payload('protected',snapshot('protected'),2),'protected')
        self.assertFalse(available_contexts(self.user).exists())
    def test_external_changes_do_not_mutate_source(self):
        RemoteChange.objects.create(organization_id=self.org.pk,resource_id=self.record.pk,base_version=1,actor_id=self.user.pk,content='Geändert',reason='Vorschlag')
        self.record.refresh_from_db();self.assertEqual(self.record.details,'VERTRAULICH')
    @override_settings(SERVER_ROLE='protected')
    def test_receiver_cannot_queue_outbound(self):
        with self.assertRaises(PermissionDenied):queue_snapshot('protected')
