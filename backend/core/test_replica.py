from django.test import TestCase,RequestFactory,override_settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Organization,User,Membership,Template,TemplateKind,Publication,ExternalDocument,PublicRecord,ExchangePolicy,ExchangeState
from .templates_service import archive
from .exchange import snapshot,receive
from .replica_views import document_access

@override_settings(EXCHANGE_SOURCE='b1d0ec0f-857c-452b-bc65-02ea198a2c4c')
class ReplicaTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association')
        self.user=User.objects.create_user(username='clerk',email='clerk@example.org')
        self.context=Membership.objects.create(user=self.user,organization=self.org,role='clerk')
        self.kind=TemplateKind.objects.create(organization=self.org,name='Beschluss')
        self.obj=Template.objects.create(organization=self.org,kind=self.kind,author=self.user,subject='Öffentlicher Betreff',markdown='INTERNER GEHEIMER TEXT',public_markdown='Freigegebener Text',classification='public_planned',state='ready')
        archive(self.obj,self.user,'Entwurf')
        ExchangePolicy.objects.create(organization=self.org,protected_enabled=True,public_enabled=True)
    def test_public_export_only_fixed_publication(self):
        self.assertNotIn('template',[x['kind'] for x in snapshot('public')['records']])
        Publication.objects.create(template=self.obj,version=1,subject='Öffentlicher Betreff',markdown='Freigegebener Text',approved_by=self.user)
        data=snapshot('public');self.assertNotIn('GEHEIMER',str(data))
        payload={'schema':1,'source':'b1d0ec0f-857c-452b-bc65-02ea198a2c4c','channel':'public','revision':1,'data':data}
        receive(payload,'public');self.assertEqual(PublicRecord.objects.get(kind='template').body,'Freigegebener Text')
    def test_private_document_manifest_scoped(self):
        data=snapshot('protected');doc=data['documents'][0]
        self.assertEqual(doc['permissions'],{str(self.context.pk):['read','export','edit']})
        self.assertEqual(doc['markdown'],'INTERNER GEHEIMER TEXT')
    def test_external_context_permissions_revalidated(self):
        obj=ExternalDocument.objects.create(id=self.obj.pk,organization_id=self.org.pk,title='Betreff',markdown='Text',version=1,permissions={str(self.context.pk):['read']})
        request=RequestFactory().get('/');request.user=self.user;request.session={'context_id':str(self.context.pk)}
        self.assertTrue(document_access(request,obj,'read'));self.assertFalse(document_access(request,obj,'export'))
        self.context.revoked_at=timezone.now();self.context.save();self.assertFalse(document_access(request,obj,'read'))
    def test_unrelated_member_receives_no_document(self):
        self.context.role='member';self.context.save();self.assertEqual(snapshot('protected')['documents'],[])
