from datetime import date
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.views.decorators.http import require_http_methods
from .models import Organization,Membership,RegistryRecord,SampleBundle,AuditEvent
from .invitations import lock_admin
from .user_views import admin_context

@transaction.atomic
def create(actor,context):
    lock_admin(actor,context.pk,context.organization_id)
    if SampleBundle.objects.filter(parent=context.organization).exists():raise ValidationError('Beispieldaten bereits vorhanden.')
    org=Organization.objects.create(name='Beispielkörperschaft · TESTDATEN',kind='municipality',primary_parent=context.organization,is_test_data=True)
    member=Membership.objects.create(user=actor,organization=org,role='organization_admin')
    records=[RegistryRecord.objects.create(organization=org,kind='committee',name='Beispielrat · TESTDATEN'),RegistryRecord.objects.create(organization=org,kind='room',name='Beispielsaal · TESTDATEN'),RegistryRecord.objects.create(organization=org,kind='term',name='Beispielperiode · TESTDATEN',starts_on=date(2024,7,1),ends_on=date(2029,6,30))]
    bundle=SampleBundle.objects.create(parent=context.organization,organization=org,membership=member,record_ids=[str(r.pk) for r in records]);AuditEvent.objects.create(actor=actor,action='samples.created',object_id=str(org.pk))
    return bundle

def check(bundle):
    org=bundle.organization
    if not org.is_test_data:raise ValidationError('Körperschaft ist nicht mehr als Testdaten markiert.')
    ids=bundle.record_ids
    if RegistryRecord.objects.filter(organization=org).count()!=len(ids) or RegistryRecord.objects.filter(pk__in=ids,version=1).count()!=len(ids):raise ValidationError('Beispieldaten wurden verändert oder ergänzt. Produktive Nutzung zunächst manuell trennen.')
    if Membership.objects.filter(organization=org).exclude(pk=bundle.membership_id).exists():raise ValidationError('Weitere Rollen vorhanden; Entfernung gesperrt.')
    # Reject any new business use or cross-organization reference. Never cascade it.
    for model in apps.get_app_config('core').get_models():
        if model in (RegistryRecord,SampleBundle,Membership):continue
        for field in model._meta.fields:
            if field.is_relation and field.remote_field.model is Organization:
                if model.objects.filter(**{field.attname:org.pk}).exists():raise ValidationError('Fachliche Referenz vorhanden; Entfernung gesperrt.')
            if field.is_relation and field.remote_field.model is RegistryRecord:
                if model.objects.filter(**{field.attname+'__in':ids}).exists():raise ValidationError('Stammdatenreferenz vorhanden; Entfernung gesperrt.')

@transaction.atomic
def remove(actor,context,bundle_id):
    lock_admin(actor,context.pk,context.organization_id)
    bundle=SampleBundle.objects.select_for_update().select_related('organization').get(pk=bundle_id,parent=context.organization)
    Organization.objects.select_for_update().get(pk=bundle.organization_id);check(bundle)
    identifier=bundle.organization_id
    RegistryRecord.objects.filter(pk__in=bundle.record_ids,organization=bundle.organization).delete()
    Membership.objects.filter(pk=bundle.membership_id).delete();Organization.objects.get(pk=identifier).delete()
    AuditEvent.objects.create(actor=actor,action='samples.removed',object_id=str(identifier))

@login_required
@require_http_methods(['GET','POST'])
def workspace(request):
    context=admin_context(request);error=''
    if request.method=='POST':
        try:
            if request.POST.get('action')=='create':create(request.user,context)
            elif request.POST.get('action')=='remove':remove(request.user,context,request.POST.get('bundle'))
            else:raise ValidationError('Unbekannte Aktion.')
        except ValidationError as exc:error=' '.join(exc.messages)
        else:return redirect('sample_data')
    bundles=SampleBundle.objects.filter(parent=context.organization).select_related('organization')
    return render(request,'sample_data.html',{'context':context,'bundles':bundles,'error':error})
