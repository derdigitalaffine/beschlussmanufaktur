import json,time
from django.test import TestCase,Client
from .models import User,AuthenticationProfile,WebAuthnCeremony
class PasskeyTests(TestCase):
    def setUp(self):self.user=User.objects.create_user('person',email='person@example.invalid',password='A-valid-password-2026')
    def test_options_anonymous_no_account_enumeration_and_replay(self):
        response=self.client.post('/sicherheit/passkeys/optionen/login/',json.dumps({}),content_type='application/json');self.assertEqual(response.status_code,200);self.assertEqual(response.json().get('allowCredentials',[]),[]);ceremony=WebAuthnCeremony.objects.get();self.assertEqual(ceremony.user_id,None)
        data=json.dumps({'id':'invalid'});self.assertEqual(self.client.post('/sicherheit/passkeys/pruefen/',data,content_type='application/json').status_code,400);ceremony.refresh_from_db();self.assertIsNotNone(ceremony.consumed_at);self.assertEqual(self.client.post('/sicherheit/passkeys/pruefen/',data,content_type='application/json').status_code,400)
    def test_registration_needs_password_recent_auth_and_browser_uv(self):
        data=json.dumps({'password':'A-valid-password-2026'})
        self.assertEqual(self.client.post('/sicherheit/passkeys/optionen/register/',data,content_type='application/json').status_code,400)
        self.client.force_login(self.user);s=self.client.session;s['authenticated_at']=int(time.time());s.save();r=self.client.post('/sicherheit/passkeys/optionen/register/',data,content_type='application/json');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['authenticatorSelection']['userVerification'],'required');self.assertEqual(r.json()['authenticatorSelection']['residentKey'],'required')
        other=Client();s=other.session;s['webauthn_ceremony']=str(WebAuthnCeremony.objects.get().pk);s.save();self.assertEqual(other.post('/sicherheit/passkeys/pruefen/',json.dumps({}),content_type='application/json').status_code,400)
