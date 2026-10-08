import uuid
from django.test import TestCase,RequestFactory,override_settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from .models import Organization,User,Membership,PortalConfiguration,PublicRecord
from .portal_configuration import configure,for_request
from .public_portal import selection
from .middleware import SecurityHeadersMiddleware
class PortalConfigurationTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.other=Organization.objects.create(name='Andere',kind='municipality')
        self.user=User.objects.create_user('admin',email='admin@example.invalid');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
        self.portal=PortalConfiguration.objects.create(organization_id=self.org.pk,domains=['rat.example.org'],organizations=[str(self.org.pk)],frame_origins=['https://kommune.example.org'])
    def test_validation_no_executable_design(self):
        for key,value in [('color','#ffffff'),('domains',['evil.org\nheader']),('frame_origins',['https://good.org/path']),('frame_origins',['https://good.org;script-src'])]:
            obj=PortalConfiguration(organization_id=self.other.pk);setattr(obj,key,value)
            with self.assertRaises(ValidationError):obj.full_clean()
    @override_settings(SERVER_ROLE='public',ALLOWED_HOSTS=['rat.example.org','testserver'])
    def test_host_scope_and_frame_boundary(self):
        PublicRecord.objects.create(id=uuid.uuid4(),organization_id=self.org.pk,kind='template',title='Sichtbar')
        PublicRecord.objects.create(id=uuid.uuid4(),organization_id=self.other.pk,kind='template',title='Anderes Portal')
        rf=RequestFactory();request=rf.get('/',HTTP_HOST='rat.example.org');self.assertEqual(selection(request).count(),1)
        response=SecurityHeadersMiddleware(lambda r:HttpResponse())(request);self.assertIn('https://kommune.example.org',response['Content-Security-Policy'])
        response=SecurityHeadersMiddleware(lambda r:HttpResponse())(rf.get('/transfer/inbox/',HTTP_HOST='rat.example.org'));self.assertIn("frame-ancestors 'none'",response['Content-Security-Policy'])
    def test_admin_cannot_include_other_unmanaged_organization(self):
        self.client.force_login(self.user);s=self.client.session;s['context_id']=str(self.ctx.pk);s.save()
        response=self.client.post('/verwaltung/portal/',{'title':'Portal','color':'#245846','scope':[str(self.other.pk)],'expected_version':1})
        self.assertEqual(response.status_code,200);self.portal.refresh_from_db();self.assertEqual(self.portal.organizations,[str(self.org.pk)])

    def test_valid_configuration_saved_and_versioned(self):
        self.client.force_login(self.user);s=self.client.session;s['context_id']=str(self.ctx.pk);s.save()
        response=self.client.post('/verwaltung/portal/',{'title':'Unser Rat','color':'#245846','scope':[str(self.org.pk)],'expected_version':1,'domains_text':'rat.example.org','frames_text':'https://kommune.example.org'})
        self.assertEqual(response.status_code,302);self.portal.refresh_from_db();self.assertEqual(self.portal.title,'Unser Rat');self.assertEqual(self.portal.version,2)
