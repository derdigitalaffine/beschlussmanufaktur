import os
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.test import TestCase,override_settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from .models import Organization,User,Membership,AuthenticationProfile,RecoveryTicket,RemoteChange,ExchangePolicy
from .recovery import issue,accept_ticket,decrypt,digest
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
class RecoveryTests(TestCase):
    def setUp(self):
        self.key=patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':Fernet.generate_key().decode()});self.key.start();self.addCleanup(self.key.stop)
        self.org=Organization.objects.create(name='VG',kind='association');self.user=User.objects.create_user('person',email='person@example.invalid',password='Old-password-2026');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='member')
    def test_token_once_and_factor_preserved_unless_controlled_reset(self):
        profile=AuthenticationProfile.objects.create(user=self.user,method='totp');ticket=issue(self.user,self.ctx);token=decrypt(ticket.encrypted_token);hashed=make_password('New-password-2026',hasher='pbkdf2_sha256');accept_ticket(ticket,hashed,token);self.user.refresh_from_db();self.assertTrue(self.user.check_password('New-password-2026'));profile.refresh_from_db();self.assertEqual(profile.method,'totp')
        with self.assertRaises(ValidationError):accept_ticket(ticket,hashed,token)
        ticket=issue(self.user,self.ctx,True);token=decrypt(ticket.encrypted_token);accept_ticket(ticket,hashed,token);profile.refresh_from_db();self.assertEqual(profile.method,'email');self.assertEqual(profile.version,1)
    def test_stale_password_or_revoked_context_cannot_reset(self):
        ticket=issue(self.user,self.ctx);token=decrypt(ticket.encrypted_token);self.user.set_password('Changed-password-2026');self.user.save()
        with self.assertRaises(ValidationError):accept_ticket(ticket,make_password('new',hasher='pbkdf2_sha256'),token)
    @override_settings(SERVER_ROLE='protected',EXCHANGE_SOURCE='b1d0ec0f-857c-452b-bc65-02ea198a2c4c',EXCHANGE_PROTECTED_KEY='p'*40)
    def test_protected_proof_staged_never_changes_account(self):
        ticket=issue(self.user,self.ctx);token=decrypt(ticket.encrypted_token);old=self.user.password
        self.client.post('/wiederherstellung/',{'token':token,'password':'New-valid-password-2026','confirmation':'New-valid-password-2026'})
        self.user.refresh_from_db();self.assertEqual(self.user.password,old);change=RemoteChange.objects.get();self.assertEqual(change.resource_kind,'credential');self.assertNotIn(token,change.content);ticket.refresh_from_db();self.assertEqual(ticket.state,'submitted')
