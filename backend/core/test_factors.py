import os,time
from unittest.mock import patch
from cryptography.fernet import Fernet
import pyotp
from django.test import TestCase,Client
from django.core.exceptions import ValidationError
from .models import User,AuthenticationProfile
from .secret_store import encrypt
from .factors import consume,recovery
class FactorTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('person',email='person@example.invalid',password='A-valid-password-2026');self.key=patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':Fernet.generate_key().decode()});self.key.start();self.addCleanup(self.key.stop)
    def test_totp_replay_and_recovery_single_use(self):
        secret=pyotp.random_base32();obj=AuthenticationProfile.objects.create(user=self.user,method='totp',secret=encrypt(secret));code=pyotp.TOTP(secret).now();self.assertTrue(consume(obj,code));self.assertFalse(consume(obj,code));codes=recovery(obj);obj.save();self.assertTrue(consume(obj,codes[0]));self.assertFalse(consume(obj,codes[0]));self.assertNotIn(codes[1],str(obj.recovery_hashes))
    def test_totp_signin_requires_factor_not_email(self):
        secret=pyotp.random_base32();AuthenticationProfile.objects.create(user=self.user,method='totp',secret=encrypt(secret))
        response=self.client.post('/anmelden/',{'email':self.user.email,'password':'A-valid-password-2026'});self.assertRedirects(response,'/anmelden/faktor/',fetch_redirect_response=False);self.assertNotIn('_auth_user_id',self.client.session)
        self.client.post('/anmelden/faktor/',{'code':pyotp.TOTP(secret).now()});self.assertIn('_auth_user_id',self.client.session)
    def test_enrollment_requires_recent_complete_login_and_password(self):
        self.client.force_login(self.user);response=self.client.post('/sicherheit/',{'password':'A-valid-password-2026','action':'start_totp'});self.assertContains(response,'erneut vollständig anmelden');self.assertFalse(AuthenticationProfile.objects.get().pending_secret)
        session=self.client.session;session['authenticated_at']=int(time.time());session.save();response=self.client.post('/sicherheit/',{'password':'A-valid-password-2026','action':'start_totp'});self.assertContains(response,'Schlüssel manuell');obj=AuthenticationProfile.objects.get();self.assertNotIn('otpauth',obj.pending_secret)
    def test_factor_version_ends_old_sessions(self):
        self.client.force_login(self.user);AuthenticationProfile.objects.create(user=self.user,version=1);response=self.client.get('/');self.assertEqual(response.status_code,302);self.assertNotIn('_auth_user_id',self.client.session)
