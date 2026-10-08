from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_POST
from .models import AccessGrant, Membership, AuditEvent, RegistryRecord,Template
from .user_views import admin_context
from .invitations import lock_admin

class GrantForm(forms.ModelForm):
    resource=forms.ChoiceField(label='Geltungsbereich und Objekt')
    actions=forms.MultipleChoiceField(label='Einzelrechte',choices=[(x,x) for x in ['read','edit','review','release','publish','export','delegate']],widget=forms.CheckboxSelectMultiple)
    class Meta:
        model=AccessGrant
        fields=['membership','actions','expires_at','reason']
        labels={'membership':'Arbeitskontext','resource_kind':'Geltungsbereich','resource_id':'Objekt-ID','expires_at':'Gültig bis','reason':'Begründung'}
        widgets={'expires_at':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')}
    def __init__(self,*args,organization,context=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.instance.organization=organization
        self.fields['membership'].queryset=Membership.objects.filter(organization=organization)
        choices=[('organization:'+str(organization.pk),'Gesamte Körperschaft: '+organization.name)]
        choices += [('registry:'+str(r.pk),r.get_kind_display()+': '+r.name) for r in RegistryRecord.objects.filter(organization=organization)]
        choices += [('unit:'+str(r.pk),'Einheit: '+r.name) for r in RegistryRecord.objects.filter(organization=organization,kind='unit')]
        from .templates_service import template_access
        choices += [('template:'+str(t.pk),'Vorlage: '+(t.subject if context and template_access(context,'read',t) else 'Inhalt nicht freigegeben · '+str(t.pk))) for t in Template.objects.filter(organization=organization)]
        self.fields['resource'].choices=choices
        self.initial['resource']='organization:'+str(organization.pk)
    def clean(self):
        cleaned=super().clean()
        if cleaned.get('resource'):
            kind,identifier=cleaned['resource'].split(':',1)
            import uuid
            self.instance.resource_kind=kind;self.instance.resource_id=uuid.UUID(identifier)
        return cleaned

@login_required
@require_http_methods(['GET','POST'])
def grants(request):
    context=admin_context(request)
    form=GrantForm(request.POST if request.method=='POST' else None,organization=context.organization,context=context,initial={'resource_kind':'organization','resource_id':context.organization_id})
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            lock_admin(request.user,context.pk,context.organization_id)
            grant=form.save()
            AuditEvent.objects.create(actor=request.user,action='access.granted',object_id=str(grant.pk),metadata={'actions':grant.actions,'reason':grant.reason,'resource':str(grant.resource_id),'membership':str(grant.membership_id)})
        return redirect('grants')
    return render(request,'grants.html',{'context':context,'form':form,'grants':AccessGrant.objects.filter(organization=context.organization).select_related('membership__user'),'records':RegistryRecord.objects.filter(organization=context.organization)})

@login_required
@require_POST
def revoke(request,grant_id):
    context=admin_context(request)
    with transaction.atomic():
        lock_admin(request.user,context.pk,context.organization_id)
        obj=get_object_or_404(AccessGrant.objects.select_for_update(),pk=grant_id,organization=context.organization)
        obj.revoked_at=timezone.now();obj.save(update_fields=['revoked_at'])
        AuditEvent.objects.create(actor=request.user,action='access.revoked',object_id=str(obj.pk))
    return redirect('grants')
