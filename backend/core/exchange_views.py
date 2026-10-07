from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import ExchangePolicy, TransferBatch, RemoteChange, RegistryRecord, AuditEvent, Membership
from .permissions import active_context, can_access, available_contexts
from .user_views import admin_context
from .invitations import lock_admin
from .exchange import queue_snapshot
from .registry import snapshot as registry_snapshot

class PolicyForm(forms.Form):
    protected_enabled=forms.BooleanField(label='Stammdaten und berechtigte Konten extern bereitstellen',required=False)
    public_enabled=forms.BooleanField(label='Name der Körperschaft und Gremien öffentlich bereitstellen',required=False)
    confirm=forms.BooleanField(label='Ich habe die Freigabe geprüft. Geschützte Konten benötigen einen eigenen erlaubten Arbeitskontext; öffentliche Ausgabe enthält keine internen Beschreibungen.')

@login_required
@require_http_methods(['GET','POST'])
def index(request):
    context=admin_context(request)
    policy=ExchangePolicy.objects.filter(organization=context.organization).first()
    form=PolicyForm(request.POST if request.method=='POST' else None,initial={'protected_enabled':policy.protected_enabled if policy else False,'public_enabled':policy.public_enabled if policy else False})
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            lock_admin(request.user,context.pk,context.organization_id)
            ExchangePolicy.objects.update_or_create(organization=context.organization,defaults={'protected_enabled':form.cleaned_data['protected_enabled'],'public_enabled':form.cleaned_data['public_enabled'],'approved_at':timezone.now(),'approved_by':request.user})
            AuditEvent.objects.create(actor=request.user,action='exchange.policy',object_id=str(context.organization_id),metadata={'protected':form.cleaned_data['protected_enabled'],'public':form.cleaned_data['public_enabled']})
        for channel in ('protected','public'):
            try:queue_snapshot(channel)
            except (PermissionDenied,ValidationError,ValueError):messages.warning(request,'Freigabe gespeichert. Dienstschlüssel und Quelle müssen vor der Übertragung konfiguriert werden.')
        return redirect('exchange')
    return render(request,'exchange.html',{'context':context,'form':form,'batches':TransferBatch.objects.defer('payload').order_by('-created_at')[:20],'changes':RemoteChange.objects.filter(organization_id=context.organization_id,state='pending')})

class ChangeForm(forms.Form):
    content=forms.CharField(label='Änderungsvorschlag',max_length=100000,widget=forms.Textarea)
    reason=forms.CharField(label='Begründung',max_length=500)
    base_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)

@login_required
@require_http_methods(['GET','POST'])
def propose(request,record_id):
    context=active_context(request)
    if not context:raise PermissionDenied
    obj=get_object_or_404(RegistryRecord,pk=record_id,organization=context.organization)
    if not can_access(context,'edit','registry',obj):raise PermissionDenied
    form=ChangeForm(request.POST if request.method=='POST' else None,initial={'content':obj.details,'base_version':obj.version})
    if request.method=='POST' and form.is_valid():
        RemoteChange.objects.create(organization_id=context.organization_id,resource_id=obj.pk,base_version=form.cleaned_data['base_version'],actor_id=request.user.pk,content=form.cleaned_data['content'],reason=form.cleaned_data['reason'])
        messages.success(request,'Vorschlag gespeichert. Intern wird er abgeholt und geprüft; der freigegebene Stand bleibt bis dahin erhalten.')
        return redirect('external_records')
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Intern zu prüfender Änderungsvorschlag'})

@login_required
@require_http_methods(['GET'])
def external_records(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    records=[r for r in RegistryRecord.objects.filter(organization=context.organization,archived=False) if can_access(context,'read','registry',r)]
    return render(request,'external_records.html',{'context':context,'records':records})

@login_required
@require_http_methods(['GET','POST'])
def review(request,change_id):
    context=admin_context(request)
    obj=get_object_or_404(RemoteChange,pk=change_id,organization_id=context.organization_id,state='pending')
    if request.method=='POST':
        with transaction.atomic():
            lock_admin(request.user,context.pk,context.organization_id)
            obj=RemoteChange.objects.select_for_update().get(pk=obj.pk)
            if obj.state!='pending':raise PermissionDenied
            if request.POST.get('decision')=='accept':
                if obj.resource_kind!='registry':raise PermissionDenied
                target=get_object_or_404(RegistryRecord.objects.select_for_update(),pk=obj.resource_id,organization=context.organization)
                # Revalidate the original actor's current authority, not just the transfer signature.
                contexts=Membership.objects.filter(user_id=obj.actor_id,organization=context.organization)
                if not any(can_access(c,'edit','registry',target) for c in contexts):raise PermissionDenied('Urheber hat keine aktuelle Berechtigung.')
                if target.version!=obj.base_version:
                    messages.error(request,'Konflikt: Der interne Stand hat sich geändert. Vorschlag bleibt zur Prüfung erhalten.');return redirect('review_remote',change_id=obj.pk)
                before=registry_snapshot(target);target.details=obj.content;target.version+=1;target.full_clean();target.save()
                AuditEvent.objects.create(actor=request.user,action='exchange.approved',object_id=str(target.pk),metadata={'change':str(obj.pk),'before':before,'after':registry_snapshot(target),'reason':obj.reason})
                obj.state='accepted'
            else:obj.state='rejected'
            obj.reviewed_by=request.user;obj.reviewed_at=timezone.now();obj.save()
        return redirect('exchange')
    return render(request,'remote_review.html',{'context':context,'change':obj})
