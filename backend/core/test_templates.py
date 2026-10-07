import tempfile
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Organization,User,Membership,Template,TemplateKind,TemplateVersion,AccessGrant,Attachment
from .templates_service import render_markdown,template_access,archive,validate_configuration

class TemplateTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association')
        self.user=User.objects.create_user(username='author',email='author@example.org')
        self.context=Membership.objects.create(user=self.user,organization=self.org,role='author')
        self.client.force_login(self.user);session=self.client.session;session['context_id']=str(self.context.pk);session.save()
    def create(self,**extra):
        data={'subject':'Straßenbau','classification':'internal','markdown':'## Beschluss\n\n**Ja**','expected_version':1,'reason':'Entwurf','kind':'default:Beschlussvorlage'};data.update(extra)
        return self.client.post('/vorlagen/neu/',data)
    def test_create_kind_and_version(self):
        self.assertEqual(self.create().status_code,302);obj=Template.objects.get();self.assertEqual(obj.version,1);self.assertEqual(obj.versions.count(),1)
        self.assertContains(self.client.get(f'/vorlagen/{obj.pk}/'),'<strong>Ja</strong>',html=True)
    def test_new_get_does_not_write(self):
        self.assertEqual(self.client.get('/vorlagen/neu/').status_code,200);self.assertFalse(TemplateKind.objects.exists())
    def test_stale_edit_does_not_overwrite(self):
        self.create();obj=Template.objects.get()
        data={'subject':'Neu','classification':'internal','markdown':'Neuer Text','expected_version':1,'reason':'Änderung'}
        self.assertEqual(self.client.post(f'/vorlagen/{obj.pk}/bearbeiten/',data).status_code,302)
        data['markdown']='Veralteter Text'
        response=self.client.post(f'/vorlagen/{obj.pk}/bearbeiten/',data)
        self.assertContains(response,'Zwischenzeitlich');self.assertContains(response,'Veralteter Text')
        obj.refresh_from_db();self.assertEqual(obj.markdown,'Neuer Text');self.assertEqual(obj.versions.count(),2)
    def test_archived_version_immutable(self):
        self.create();v=TemplateVersion.objects.get();v.reason='Manipulation'
        with self.assertRaises(ValidationError):v.save()
    def test_author_cannot_read_other_author(self):
        self.create();obj=Template.objects.get();other=User.objects.create_user(username='other',email='other@example.org')
        obj.author=other;obj.save();self.assertEqual(self.client.get(f'/vorlagen/{obj.pk}/').status_code,403)
    def test_administration_needs_explicit_content_right(self):
        self.create();obj=Template.objects.get();self.context.role='organization_admin';self.context.save()
        self.assertFalse(template_access(self.context,'read',obj))
        AccessGrant.objects.create(organization=self.org,membership=self.context,resource_kind='template',resource_id=obj.pk,actions=['read'],reason='Prüfung')
        self.assertTrue(template_access(self.context,'read',obj))
    def test_xss_and_network_images_removed(self):
        text=render_markdown('<script>alert(1)</script><img src="http://internal/" onerror="alert(1)"> [Link](javascript:alert(1))')
        for bad in ['<script','<img','onerror','javascript:']:self.assertNotIn(bad,text)
    def test_configuration_schema(self):
        with self.assertRaises(ValidationError):validate_configuration([{'key':'x','label':'X'},{'key':'x','label':'X'}],[])
    def test_private_upload_download_permissions(self):
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            self.create();obj=Template.objects.get()
            r=self.client.post(f'/vorlagen/{obj.pk}/anlagen/',{'expected_version':1,'file':SimpleUploadedFile('../../note.txt',b'Nicht oeffentlich',content_type='text/plain')})
            self.assertEqual(r.status_code,302);a=Attachment.objects.get();self.assertFalse(a.checked);self.assertFalse(a.public)
            response=self.client.get(f'/anlagen/{a.pk}/');self.assertEqual(response.status_code,200);self.assertEqual(b''.join(response.streaming_content),b'Nicht oeffentlich')
            self.context.role='member';self.context.save();self.assertEqual(self.client.get(f'/anlagen/{a.pk}/').status_code,403)
    def test_fake_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            self.create();obj=Template.objects.get();self.client.post(f'/vorlagen/{obj.pk}/anlagen/',{'expected_version':1,'file':SimpleUploadedFile('evil.pdf',b'<script>alert(1)</script>')})
            self.assertFalse(Attachment.objects.exists())
    def test_required_custom_field(self):
        kind=TemplateKind.objects.create(organization=self.org,name='Eigene',fields=[{'key':'summe','label':'Summe','type':'number','required':True}])
        self.create(kind=str(kind.pk));self.assertFalse(Template.objects.exists())
        self.assertEqual(self.create(kind=str(kind.pk),extra_summe='1200.50').status_code,302)
    def test_compare_escaped(self):
        self.create(markdown='<script>bad</script>');obj=Template.objects.get()
        r=self.client.get(f'/vorlagen/{obj.pk}/version/1/');self.assertContains(r,'&lt;script&gt;');self.assertNotContains(r,'<script>bad')
