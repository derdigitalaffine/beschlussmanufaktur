import io,uuid,json
from PIL import Image
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from .models import PersonProfile,User,Organization,Membership,ExchangePolicy
from .person_profiles import projection,sanitize_photo
from .public_portal import validate_metadata
from .exchange import snapshot
class PersonProfileTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.user=User.objects.create_user('person',email='private@example.invalid');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
        self.profile=PersonProfile.objects.create(organization=self.org,user=self.user,name='Anna',contact='Privater Kontakt',public_fields=['name'],published=True)
    def test_explicit_field_projection_excludes_account_and_contact(self):
        data=projection(self.profile);text=json.dumps(data);self.assertNotIn(self.user.email,text);self.assertNotIn('Privater Kontakt',text);self.assertNotIn('user',data['metadata']);self.assertEqual(data['metadata'],{'name':'Anna'})
    def test_portrait_sanitized_and_untrusted_metadata_rejected(self):
        b=io.BytesIO();Image.new('RGB',(1200,800)).save(b,format='PNG');photo=sanitize_photo(SimpleUploadedFile('test.png',b.getvalue()));validate_metadata({'photo':photo},'person')
        with self.assertRaises(ValidationError):validate_metadata({'email':'private@example.invalid'},'person')
        with self.assertRaises(ValidationError):validate_metadata({'photo':'<svg/>'},'person')
    def test_valid_save_and_foreign_account_blocked(self):
        self.client.force_login(self.user);s=self.client.session;s['context_id']=str(self.ctx.pk);s.save()
        payload={'name':'Anna','user':self.user.pk,'expected_version':1,'reason':'Freigabe','public_fields':['name'],'published':'on'}
        response=self.client.post('/verwaltung/personen/'+str(self.profile.pk)+'/',payload);self.assertEqual(response.status_code,302)
        foreign=User.objects.create_user('other',email='other@example.invalid');payload.update(user=foreign.pk,expected_version=2)
        self.assertEqual(self.client.post('/verwaltung/personen/'+str(self.profile.pk)+'/',payload).status_code,200);self.profile.refresh_from_db();self.assertEqual(self.profile.user_id,self.user.pk)
