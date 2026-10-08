import base64,hashlib,hmac,json,secrets
from datetime import timedelta
from cryptography.fernet import Fernet
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password,identify_hasher
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render,redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import RecoveryTicket,User,Membership,RemoteChange,AuthenticationProfile,Passkey,AuditEvent,TransferBatch,ExchangePolicy
from .permissions import available_contexts
from .services import consume_rate_limit
from .network import client_address
from .secret_store import encrypt,decrypt
from .user_views import admin_context
from .invitations import lock_admin

FIELDS=['id','user_id','organization_id','context_id','token_digest','password_basis','expires_at','state','reset_factor']
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def proof_cipher():
    from .exchange import key
    return Fernet(base64.urlsafe_b64encode(hmac.new(key('protected'),b'recovery-proof-v1',hashlib.sha256).digest()))

def issue(user,context,reset_factor=False):
    token=secrets.token_urlsafe(32)
    RecoveryTicket.objects.filter(user=user,state='pending').update(state='cancelled',encrypted_token='')
    obj=RecoveryTicket.objects.create(user=user,organization_id=context.organization_id,context_id=context.pk,token_digest=digest(token),password_basis=digest(user.password),expires_at=timezone.now()+timedelta(hours=1),reset_factor=reset_factor,encrypted_token=encrypt(token))
    AuditEvent.objects.create(actor=user,action='recovery.issued',object_id=str(obj.pk),metadata={'reset_factor':reset_factor})
    return obj

def reset_local_factor(user):
    obj,_=AuthenticationProfile.objects.get_or_create(user=user);obj.method='email';obj.secret='';obj.pending_secret='';obj.pending_expires_at=None;obj.recovery_hashes=[];obj.version+=1;obj.save();Passkey.objects.filter(user=user).delete()

@transaction.atomic
def accept_ticket(obj,password_hash,token):
    user=User.objects.select_for_update().get(pk=obj.user_id,is_active=True)
    if obj.state!='pending' or obj.expires_at<=timezone.now() or digest(token)!=obj.token_digest or digest(user.password)!=obj.password_basis or not available_contexts(user).filter(pk=obj.context_id,organization_id=obj.organization_id).exists():raise ValidationError('Wiederherstellung abgelaufen oder nicht mehr gültig.')
    hasher=identify_hasher(password_hash)
    if hasher.algorithm!='pbkdf2_sha256' or len(password_hash)>256:raise ValidationError('Ungültiger Passwortnachweis.')
    values=hasher.decode(password_hash)
    if not hasher.iterations<=values['iterations']<=2*hasher.iterations or len(values['salt'])<12:raise ValidationError('Ungültige Passwortstärke im Nachweis.')
    user.password=password_hash;user.save(update_fields=['password']);obj.state='approved';obj.encrypted_token='';obj.save(update_fields=['state','encrypted_token'])
    if obj.reset_factor:reset_local_factor(user)
    AuditEvent.objects.create(actor=user,action='recovery.approved',object_id=str(obj.pk),metadata={'reset_factor':obj.reset_factor})

def send_pending():
    if settings.SERVER_ROLE!='internal':return
    from .exchange import REMOTE_ROLES
    for identifier in RecoveryTicket.objects.filter(state='pending',delivered_at__isnull=True,attempts__lt=10,expires_at__gt=timezone.now()).values_list('pk',flat=True)[:20]:
        with transaction.atomic():
            obj=RecoveryTicket.objects.select_for_update().select_related('user').get(pk=identifier)
            if obj.delivered_at or obj.state!='pending':continue
            ctx=available_contexts(obj.user).filter(pk=obj.context_id).first()
            if not ctx:continue
            external=ctx.role in REMOTE_ROLES and ExchangePolicy.objects.filter(organization_id=obj.organization_id,protected_enabled=True).exists()
            if external:
                ready=any(any(r['id']==str(obj.pk) for r in b.payload['data'].get('recovery',[])) for b in TransferBatch.objects.filter(channel='protected',delivered_at__isnull=False).order_by('-revision')[:5])
                if not ready:continue
            origin=settings.EXCHANGE_PROTECTED_URL if external else settings.APPLICATION_URL
            obj.attempts+=1
            try:
                token=decrypt(obj.encrypted_token);send_mail('Wiederherstellung Ihres Zugangs','Für Ihr Konto wurde eine kontrollierte Wiederherstellung angefordert. Link: '+origin+'/wiederherstellung/#'+token+'\n\nCode: '+token+'\n\nGültigkeit: eine Stunde. Wenn Sie dies nicht angefordert haben, informieren Sie die Administration.',None,[obj.user.email])
            except Exception:pass
            else:obj.delivered_at=timezone.now();obj.encrypted_token=''
            obj.save(update_fields=['attempts','delivered_at','encrypted_token'])

class RequestForm(forms.Form):email=forms.EmailField(label='Persönliche E-Mail-Adresse')
class ResetForm(forms.Form):
    token=forms.CharField(label='Wiederherstellungscode aus Ihrer E-Mail',min_length=43,max_length=43)
    password=forms.CharField(label='Neues Passwort',widget=forms.PasswordInput)
    confirmation=forms.CharField(label='Neues Passwort wiederholen',widget=forms.PasswordInput)

@require_http_methods(['GET','POST'])
def request_reset(request):
    form=RequestForm(request.POST or None);submitted=False
    if request.method=='POST' and form.is_valid():
        submitted=True;email=form.cleaned_data['email'].lower()
        if consume_rate_limit('recovery-ip:'+client_address(request),20) and consume_rate_limit('recovery-email:'+email,3):
            user=User.objects.filter(email=email,is_active=True).first()
            ctx=available_contexts(user).first() if user else None
            if ctx:
                try:
                    if settings.SERVER_ROLE=='internal':issue(user,ctx)
                    else:RemoteChange.objects.create(organization_id=ctx.organization_id,resource_id=ctx.pk,resource_kind='recovery_request',context_id=ctx.pk,actor_id=user.pk,base_version=ctx.version,content='',reason='Wiederherstellung angefordert; Administration prüft den Zugang.')
                except ValidationError:pass
    return render(request,'recovery.html',{'form':form,'submitted':submitted,'request_step':True})

@require_http_methods(['GET','POST'])
def reset(request):
    form=ResetForm(request.POST or None);done=False
    if request.method=='POST' and form.is_valid():
        try:
            if not consume_rate_limit('recovery-proof:'+client_address(request),10):raise ValidationError('Zu viele Versuche.')
            data=form.cleaned_data
            if data['password']!=data['confirmation']:raise ValidationError('Passwörter stimmen nicht überein.')
            with transaction.atomic():
                obj=RecoveryTicket.objects.select_for_update().select_related('user').filter(token_digest=digest(data['token']),state='pending',expires_at__gt=timezone.now()).first()
                if not obj or digest(obj.user.password)!=obj.password_basis:raise ValidationError('Code ungültig oder abgelaufen.')
                validate_password(data['password'],obj.user)
                hashed=make_password(data['password'],hasher='pbkdf2_sha256')
                if settings.SERVER_ROLE=='internal':accept_ticket(obj,hashed,data['token'])
                else:
                    content=proof_cipher().encrypt(json.dumps({'token':data['token'],'password_hash':hashed}).encode()).decode()
                    RemoteChange.objects.create(organization_id=obj.organization_id,resource_id=obj.pk,resource_kind='credential',context_id=obj.context_id,actor_id=obj.user_id,base_version=1,content=content,reason='E-Mail-Wiederherstellungscode bestätigt; neue Zugangsdaten intern prüfen.')
                    obj.state='submitted';obj.save(update_fields=['state'])
            done=True
        except ValidationError as exc:form.add_error(None,exc)
    return render(request,'recovery.html',{'form':form,'done':done})

@login_required
@require_http_methods(['GET','POST'])
def administrative(request):
    context=admin_context(request)
    class AdminForm(forms.Form):
        member=forms.ModelChoiceField(label='Zugehöriges persönliches Konto',queryset=Membership.objects.filter(organization=context.organization,user__is_active=True))
        reset_factor=forms.BooleanField(label='Auch verlorene Faktoren nach Identitätsprüfung zurücksetzen (Betriebsrolle erforderlich)',required=False)
        reason=forms.CharField(label='Identitätsprüfung und Begründung',max_length=500)
    form=AdminForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                lock_admin(request.user,context.pk,context.organization_id);member=form.cleaned_data['member']
                if not available_contexts(member.user).filter(pk=member.pk).exists():raise ValidationError('Zuweisung nicht mehr gültig.')
                if form.cleaned_data['reset_factor']:
                    from .operators import require_operator
                    require_operator(request)
                obj=issue(member.user,member,form.cleaned_data['reset_factor']);AuditEvent.objects.create(actor=request.user,action='recovery.admin_issued',object_id=str(obj.pk),metadata={'reason':form.cleaned_data['reason']})
        except ValidationError as exc:form.add_error(None,exc)
        else:return redirect('recovery_admin')
    return render(request,'admin_form.html',{'context':context,'form':form,'title':'Kontrollierte Zugangswiederherstellung','description':'Nur die hinterlegte persönliche E-Mail erhält den Code. Öffentliche Rückmeldungen werden intern geprüft.'})
