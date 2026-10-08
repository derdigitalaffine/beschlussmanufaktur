import io
from django.test import TestCase,RequestFactory
from django.core.exceptions import ValidationError
from pypdf import PdfReader
from docx import Document
from .models import Organization,User,Membership,TemplateKind,PortalConfiguration
from .configuration_editor import sets,build,fingerprint
from .document_export import export
from .access_views import GrantForm
class ConfigurationEditorTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.user=User.objects.create_user('admin',email='admin@example.invalid');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
    def test_typed_fields_parallel_conditions_and_simple_mode_preserves(self):
        self.client.force_login(self.user);s=self.client.session;s['context_id']=str(self.ctx.pk);s.save()
        obj=TemplateKind.objects.create(organization=self.org,name='Beschluss',fields=[{'key':'kosten','label':'Kosten','type':'number'}],workflow=[{'name':'FBL','role':'reviewer','group':1}])
        response=self.client.post('/vorlagenarten/'+str(obj.pk)+'/',{'name':'Beschluss neu','initial_markdown':'Text','expected':fingerprint(obj)})
        self.assertEqual(response.status_code,302);obj.refresh_from_db();self.assertEqual(obj.fields[0]['key'],'kosten')
        self.user.advanced_mode=True;self.user.save();response=self.client.get('/vorlagenarten/'+str(obj.pk)+'/');self.assertContains(response,'fields-TOTAL_FORMS');self.assertNotContains(response,'Pflichtfelder (JSON)')
    def test_named_resource_selection(self):
        form=GrantForm({'membership':str(self.ctx.pk),'resource':'organization:'+str(self.org.pk),'actions':['read'],'reason':'Prüfung'},organization=self.org,context=self.ctx);self.assertTrue(form.is_valid(),form.errors);self.assertEqual(form.instance.resource_id,self.org.pk)
    def test_branding_pdf_docx(self):
        PortalConfiguration.objects.create(organization_id=self.org.pk,title='VG Beispiel',color='#19382e')
        pdf,_=export('Titel','## Text','pdf',organization_id=self.org.pk);self.assertIn('VG Beispiel',PdfReader(io.BytesIO(pdf)).pages[0].extract_text())
        docx,_=export('Titel','Text','docx',organization_id=self.org.pk);self.assertEqual(Document(io.BytesIO(docx)).sections[0].header.paragraphs[0].text,'VG Beispiel')
    def test_advanced_editor_saves_parallel_conditional_configuration(self):
        self.user.advanced_mode=True;self.user.save();self.client.force_login(self.user);s=self.client.session;s['context_id']=str(self.ctx.pk);s.save()
        obj=TemplateKind.objects.create(organization=self.org,name='Beschluss')
        payload={'name':'Beschluss','expected':fingerprint(obj),'fields-TOTAL_FORMS':'1','fields-INITIAL_FORMS':'0','fields-0-key':'kosten','fields-0-label':'Kosten','fields-0-type':'number','steps-TOTAL_FORMS':'2','steps-INITIAL_FORMS':'0','steps-0-name':'FBL','steps-0-role':'reviewer','steps-0-group':'1','steps-0-condition_field':'kosten','steps-0-condition_value':'10','steps-1-name':'Freigabe','steps-1-role':'release','steps-1-group':'1'}
        response=self.client.post('/vorlagenarten/'+str(obj.pk)+'/',payload);self.assertEqual(response.status_code,302,response.content[:1000]);obj.refresh_from_db();self.assertEqual(obj.workflow[0]['condition']['equals'],10);self.assertEqual(obj.workflow[1]['group'],1)
