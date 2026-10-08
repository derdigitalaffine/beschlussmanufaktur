from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import EmergencyAccess,Organization,Membership,AccessGrant,MeetingGuest,Meeting,Template,AuditEvent,SystemOperator
from .operators import require_operator
from .user_views import admin_context
from .invitations import lock_admin

class RequestForm(forms.Form):
    organization=forms.ModelChoiceField(label='Zuständige Körperschaft',queryset=Organization.objects.all())
    resource_kind=forms.ChoiceField(label='Objektart',choices=[('template','Vorlage'),('meeting','Sitzung')])
    resource_id=forms.UUIDField(label='Vom Fachverantwortlichen benannte Objekt-ID')
    reason=forms.CharField(label='Notfall und Zweck',max_length=500,widget=forms.Textarea)
    minutes=forms.IntegerField(label='Dauer in Minuten',min_value=5,max_value=120,initial=30)

@transaction.atomic
def approve(context,identifier,accept):
    lock_admin(context.user,context.pk,context.organization_id)
    obj=EmergencyAccess.objects.select_for_update().get(pk=identifier,organization=context.organization,state='pending')
    if obj.operator_id==context.user_id:raise PermissionDenied('Notfallzugriff benötigt eine andere fachlich verantwortliche Person.')
    if obj.expires_at<=timezone.now() or not SystemOperator.objects.filter(user=obj.operator,enabled=True).exists():raise ValidationError('Antrag abgelaufen oder Betriebsrolle beendet.')
    if accept:
        target=(Template if obj.resource_kind=='template' else Meeting).objects.filter(pk=obj.resource_id,organization=context.organization).first()
        if not target:raise ValidationError('Objekt gehört nicht zur Körperschaft oder ist nicht vorhanden.')
        obj.membership=Membership.objects.create(user=obj.operator,organization=context.organization,role='emergency',ends_at=obj.expires_at)
        if obj.resource_kind=='template':
            grant=AccessGrant(organization=context.organization,membership=obj.membership,resource_kind='template',resource_id=obj.resource_id,actions=['read','export'],expires_at=obj.expires_at,reason='Notfall: '+obj.reason[:490]);grant.full_clean();grant.save()
        else:MeetingGuest.objects.create(meeting=target,membership=obj.membership,expires_at=obj.expires_at,private=True)
        obj.state='approved'
    else:obj.state='rejected'
    obj.reviewed_by=context.user;obj.save();AuditEvent.objects.create(actor=context.user,action='emergency.'+obj.state,object_id=str(obj.pk),metadata={'operator':obj.operator_id,'reason':obj.reason,'expires':obj.expires_at.isoformat(),'resource':str(obj.resource_id)})
    transaction.on_commit(lambda:notify(obj))
    return obj

def notify(obj):
    from django.conf import settings
    recipients=list(Membership.objects.filter(organization=obj.organization,role='organization_admin',revoked_at__isnull=True,user__is_active=True).values_list('user__email',flat=True))
    try:send_mail('Notfallzugriff: Prüfung erforderlich','Ein begründeter Notfallzugriff wurde '+obj.state+'. Prüfen Sie das interne Audit und die eingestellte Ablaufzeit.',None,list(set(recipients)))
    except Exception:AuditEvent.objects.create(action='emergency.notice_failed',object_id=str(obj.pk))

@login_required
@require_http_methods(['GET','POST'])
def request_access(request):
    require_operator(request);form=RequestForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data
        obj=EmergencyAccess.objects.create(operator=request.user,organization=data['organization'],resource_kind=data['resource_kind'],resource_id=data['resource_id'],reason=data['reason'],expires_at=timezone.now()+timedelta(minutes=data['minutes']))
        AuditEvent.objects.create(actor=request.user,action='emergency.requested',object_id=str(obj.pk),metadata={'reason':obj.reason});notify(obj);return redirect('emergency_request')
    return render(request,'emergency.html',{'form':form,'requests':EmergencyAccess.objects.filter(operator=request.user).order_by('-created_at')[:30],'technical':True})

@login_required
@require_http_methods(['GET','POST'])
def review(request):
    context=admin_context(request);error=''
    if request.method=='POST':
        try:approve(context,request.POST.get('request'),request.POST.get('decision')=='approve')
        except ValidationError as exc:error=' '.join(exc.messages)
        else:return redirect('emergency_review')
    return render(request,'emergency.html',{'context':context,'requests':EmergencyAccess.objects.filter(organization=context.organization).order_by('-created_at')[:30],'error':error})
