from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import User, Organization, Membership, RegistryRecord, Mandate, AuditEvent
from .registry import MandateForm

class RegistryTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='admin',email='admin@example.org')
        self.org=Organization.objects.create(name='VG',kind='association')
        self.context=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
        self.client.force_login(self.user)
        session=self.client.session;session['context_id']=str(self.context.pk);session.save()
        self.other=Organization.objects.create(name='Andere',kind='union')
    def record(self,kind,name=None,organization=None,**kwargs):
        return RegistryRecord.objects.create(organization=organization or self.org,kind=kind,name=name or kind,**kwargs)
    def test_scoped_index(self):
        self.record('committee','Geheimes Fremdgremium',self.other)
        r=self.client.get('/stammdaten/')
        self.assertEqual(r.status_code,200);self.assertNotContains(r,'Geheimes Fremdgremium')
    def test_foreign_edit_denied(self):
        obj=self.record('committee',organization=self.other)
        self.assertEqual(self.client.get(f'/stammdaten/record/{obj.pk}/').status_code,404)
    def test_create_and_conflict_and_history(self):
        data={'kind':'committee','name':'Rat','expected_version':1,'reason':'Einrichtung'}
        self.assertEqual(self.client.post('/stammdaten/record/neu/',data).status_code,302)
        obj=RegistryRecord.objects.get(name='Rat')
        data['name']='Gemeinderat'
        self.assertEqual(self.client.post(f'/stammdaten/record/{obj.pk}/',data).status_code,302)
        data['name']='Veraltete Änderung'
        r=self.client.post(f'/stammdaten/record/{obj.pk}/',data)
        self.assertContains(r,'Zwischenzeitlich')
        obj.refresh_from_db();self.assertEqual(obj.name,'Gemeinderat')
        self.assertEqual(AuditEvent.objects.filter(action='registry.saved').last().metadata['before']['name'],'Rat')
    def test_period_required(self):
        r=self.client.post('/stammdaten/record/neu/',{'kind':'term','name':'2024','expected_version':1,'reason':'Einrichtung'})
        self.assertEqual(r.status_code,200);self.assertFalse(RegistryRecord.objects.exists())
    def test_no_implicit_superuser(self):
        self.context.role='member';self.context.save();self.user.is_superuser=True;self.user.save()
        self.assertEqual(self.client.get('/stammdaten/').status_code,403)
    def test_mandate_foreign_fields_rejected(self):
        committee=self.record('committee');term=self.record('term',starts_on=date(2024,1,1),ends_on=date(2029,12,31))
        function=self.record('function',organization=self.other)
        obj=Mandate(committee=committee,term=term,function=function,user=self.user,starts_on=date(2024,1,1),ends_on=date(2029,12,31))
        with self.assertRaises(ValidationError):obj.full_clean()
    def test_mandate_form_account_scope(self):
        foreign=User.objects.create_user(username='foreign',email='foreign@example.org')
        form=MandateForm(organization=self.org)
        self.assertNotIn(foreign,form.fields['user'].queryset)
    def test_context_expiry_effective(self):
        from django.utils import timezone
        self.context.revoked_at=timezone.now();self.context.save()
        self.assertEqual(self.client.get('/stammdaten/').status_code,403)
    def test_structure_cycle(self):
        child=Organization.objects.create(name='Kind',kind='municipality',primary_parent=self.org)
        self.org.primary_parent=child
        with self.assertRaises(ValidationError):self.org.full_clean()
    def test_invalid_kind_404(self):
        self.assertEqual(self.client.get('/stammdaten/unknown/neu/').status_code,404)
    def test_mode_remembered(self):
        self.client.post('/ansicht/',{'mode':'advanced'})
        self.user.refresh_from_db();self.assertTrue(self.user.advanced_mode)
        self.org.advanced_enabled=False;self.org.save()
        self.client.post('/ansicht/',{'mode':'advanced'})
        self.user.refresh_from_db();self.assertFalse(self.user.advanced_mode)
