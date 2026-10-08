import secrets,time
from datetime import timedelta
import pyotp
from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password,check_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect,render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import AuthenticationProfile,User,AuditEvent
from .secret_store import encrypt,decrypt
from .services import consume_rate_limit
from .network import client_address

class FactorCodeForm(forms.Form):
    code=forms.CharField(label='Authenticator-Code oder einmaliger Wiederherstellungscode',max_length=50,widget=forms.TextInput(attrs={'autocomplete':'one-time-code'}))
class SecurityForm(forms.Form):
    password=forms.CharField(label='Aktuelles Passwort',widget=forms.PasswordInput)
    code=forms.CharField(label='Authenticator-/Wiederherstellungscode (bei aktivem Authenticator)',max_length=50,required=False)


def method(user):return AuthenticationProfile.objects.filter(user=user).values_list('method',flat=True).first() or 'email'

def authenticated(request,user,backend='django.contrib.auth.backends.ModelBackend'):
    login(request,user,backend=backend);request.session['authenticated_at']=int(time.time())
    request.session['factor_version']=AuthenticationProfile.objects.filter(user=user).values_list('version',flat=True).first() or 0

def consume(profile,code):
    # Caller holds profile row lock. Counter is monotonic and shared by all sessions.
    if profile.method=='totp' and profile.secret:
        totp=pyotp.TOTP(decrypt(profile.secret));counter=int(time.time())//totp.interval
        for candidate in (counter-1,counter,counter+1):
            if candidate>profile.last_counter and secrets.compare_digest(totp.generate_otp(candidate),code):
                profile.last_counter=candidate;profile.save(update_fields=['last_counter']);return True
    for encoded in list(profile.recovery_hashes):
        if check_password(code,encoded):
            profile.recovery_hashes.remove(encoded);profile.save(update_fields=['recovery_hashes']);return True
    return False

def recovery(profile):
    values=[secrets.token_hex(10) for _ in range(10)]
    profile.recovery_hashes=[make_password(x) for x in values];return values

@require_http_methods(['GET','POST'])
def verify(request):
    pending=request.session.get('pending_factor',{})
    if pending.get('expires',0)<time.time():request.session.pop('pending_factor',None);return redirect('sign_in')
    form=FactorCodeForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        valid=False
        if consume_rate_limit('factor-ip:'+client_address(request),30) and consume_rate_limit('factor-user:'+str(pending.get('user')),10):
            with transaction.atomic():
                user=User.objects.select_for_update().filter(pk=pending.get('user'),is_active=True).first()
                profile=AuthenticationProfile.objects.select_for_update().filter(user=user,method=pending.get('method')).first() if user else None
                valid=bool(profile and consume(profile,form.cleaned_data['code']))
        if valid:
            request.session.pop('pending_factor',None);authenticated(request,user);AuditEvent.objects.create(actor=user,action='authentication.factor_verified');return redirect('home')
        form.add_error(None,'Code ungültig, bereits verwendet oder zu viele Versuche.')
    return render(request,'auth.html',{'form':form,'title':'Anmeldung bestätigen','description':'Verwenden Sie Ihren Authenticator oder einen einmaligen Wiederherstellungscode.','button':'Sicher anmelden','code_step':True})

@login_required
@require_http_methods(['GET','POST'])
def security(request):
    profile,_=AuthenticationProfile.objects.get_or_create(user=request.user)
    form=SecurityForm(request.POST or None);secret='';uri='';codes=[]
    if request.method=='POST' and form.is_valid():
        try:
            if time.time()-request.session.get('authenticated_at',0)>300:raise ValidationError('Bitte erneut vollständig anmelden; die Sicherheitsbestätigung gilt fünf Minuten.')
            if not consume_rate_limit('factor-change:'+str(request.user.pk),10) or not request.user.check_password(form.cleaned_data['password']):raise ValidationError('Passwort ungültig oder zu viele Versuche.')
            with transaction.atomic():
                user=User.objects.select_for_update().get(pk=request.user.pk,is_active=True)
                profile=AuthenticationProfile.objects.select_for_update().get(user=user)
                if profile.method!='email' and not (profile.method=='passkey' and request.session.get('passkey_reauthenticated_at',0)>time.time()-300) and not consume(profile,form.cleaned_data['code']):raise ValidationError('Aktuellen zweiten Faktor oder Wiederherstellungscode bestätigen.')
                action=request.POST.get('action')
                if action=='start_totp':
                    secret=pyotp.random_base32();profile.pending_secret=encrypt(secret);profile.pending_expires_at=timezone.now()+timedelta(minutes=5);uri=pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='Beschlussmanufaktur')
                elif action=='confirm_totp':
                    if not profile.pending_secret or profile.pending_expires_at<=timezone.now():raise ValidationError('Einrichtung abgelaufen. Neu beginnen.')
                    pending=decrypt(profile.pending_secret);totp=pyotp.TOTP(pending)
                    counter=int(time.time())//30
                    matching=next((c for c in (counter-1,counter,counter+1) if secrets.compare_digest(totp.generate_otp(c),request.POST.get('new_code',''))),None)
                    if matching is None:raise ValidationError('Neuen Authenticator-Code prüfen.')
                    profile.secret=profile.pending_secret;profile.pending_secret='';profile.pending_expires_at=None;profile.method='totp';profile.last_counter=matching;profile.version+=1;codes=recovery(profile)
                elif action=='email':
                    # Existing configured factor was verified above. No silent fallback.
                    profile.method='email';profile.secret='';profile.pending_secret='';profile.pending_expires_at=None;profile.recovery_hashes=[];profile.version+=1
                elif action=='recovery':codes=recovery(profile);profile.version+=1
                else:raise ValidationError('Unbekannte Sicherheitsaktion.')
                profile.save();request.session['factor_version']=profile.version
                AuditEvent.objects.create(actor=user,action='authentication.factor_changed',metadata={'operation':action,'method':profile.method})
                if action!='start_totp':transaction.on_commit(lambda:notify_change(user))
        except ValidationError as exc:form.add_error(None,exc)
    return render(request,'security.html',{'form':form,'profile':profile,'secret':secret,'uri':uri,'codes':codes})

def notify_change(user):
    try:send_mail('Sicherheitseinstellungen geändert','Die Anmeldesicherheit Ihres Kontos wurde geändert. Bei einer unbekannten Änderung wenden Sie sich an Ihre Administration.',None,[user.email])
    except Exception:AuditEvent.objects.create(actor=user,action='authentication.notice_failed')
