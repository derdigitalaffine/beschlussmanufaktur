from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_POST
from .models import AccessGrant, Membership, AuditEvent, RegistryRecord
from .user_views import admin_context
from .invitations import lock_admin

class GrantForm(forms.ModelForm):
    actions=forms.MultipleChoiceField(label='Einzelrechte',choices=[(x,x) for x in ['read','edit','review','release','publish','export','delegate']],widget=forms.CheckboxSelectMultiple)
    class Meta:
        model=AccessGrant
        fields=['membership','resource_kind','resource_id','actions','expires_at','reason']
        labels={'membership':'Arbeitskontext','resource_kind':'Geltungsbereich','resource_id':'Objekt-ID','expires_at':'Gültig bis','reason':'Begründung'}
        widgets={'expires_at':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')}
    def __init__(self,*args,organization,**kwargs):
        super().__init__(*args,**kwargs)
        self.instance.organization=organization
        self.fields['membership'].queryset=Membership.objects.filter(organization=organization)
        self.fields['resource_kind'].choices=[('organization','Gesamte Körperschaft'),('registry','Gremium / Stammdatensatz'),('unit','Organisationseinheit'),('template','Vorlage')]

@login_required
@require_http_methods(['GET','POST'])
def grants(request):
    context=admin_context(request)
    form=GrantForm(request.POST if request.method=='POST' else None,organization=context.organization,initial={'resource_kind':'organization','resource_id':context.organization_id})
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
