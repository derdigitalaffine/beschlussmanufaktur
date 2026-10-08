import json,secrets,time
from datetime import timedelta
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction,IntegrityError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_GET,require_POST
from webauthn import generate_registration_options,generate_authentication_options,verify_registration_response,verify_authentication_response,options_to_json,base64url_to_bytes
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import AuthenticatorSelectionCriteria,ResidentKeyRequirement,UserVerificationRequirement,PublicKeyCredentialDescriptor
from .models import Passkey,WebAuthnCeremony,AuthenticationProfile,User,AuditEvent
from .factors import SecurityForm,consume,recovery,authenticated,notify_change
from .services import consume_rate_limit
from .network import client_address

def origin():return settings.APPLICATION_URL

def session_digest(request):
    if not request.session.session_key:request.session.create()
    return salted_hmac('webauthn-session',request.session.session_key,algorithm='sha256').hexdigest()

def confirmed(request,data):
    if not request.user.is_authenticated or time.time()-request.session.get('authenticated_at',0)>300:raise PermissionDenied('Frische vollständige Anmeldung erforderlich.')
    form=SecurityForm(data)
    if not form.is_valid() or not request.user.check_password(form.cleaned_data['password']):raise PermissionDenied('Aktuelles Passwort erforderlich.')
    profile,_=AuthenticationProfile.objects.get_or_create(user=request.user)
    recent=request.session.get('passkey_reauthenticated_at',0)>time.time()-300
    if profile.method!='email' and not (profile.method=='passkey' and recent) and not consume(profile,form.cleaned_data['code']):raise PermissionDenied('Aktuellen Faktor oder Wiederherstellungscode bestätigen.')
    return profile

def body(request):
    if len(request.body)>30000:raise ValidationError('Antwort zu groß.')
    data=json.loads(request.body)
    if not isinstance(data,dict):raise ValidationError('Ungültige Antwort.')
    return data

@login_required
@require_GET
def workspace(request):return render(request,'passkeys.html',{'keys':Passkey.objects.filter(user=request.user),'profile':AuthenticationProfile.objects.filter(user=request.user).first()})

@require_POST
def options(request,purpose):
    try:
        if purpose not in ('register','login','reauth'):raise ValidationError('Unbekannter Vorgang.')
        if not consume_rate_limit('passkey-ip:'+client_address(request),30):raise PermissionDenied
        data=body(request);challenge=secrets.token_bytes(32);name=str(data.get('name','Passkey')).strip()[:80] or 'Passkey'
        with transaction.atomic():
            profile=None;user=None
            if purpose=='register':
                if not request.user.is_authenticated:raise PermissionDenied
                User.objects.select_for_update().get(pk=request.user.pk,is_active=True)
                profile=confirmed(request,data);user=request.user
                if Passkey.objects.filter(user=user).count()>=10:raise ValidationError('Maximal zehn Passkeys.')
                handle=Passkey.objects.filter(user=user).values_list('user_handle',flat=True).first() or secrets.token_hex(32)
                request.session['webauthn_handle']=handle
                result=generate_registration_options(rp_id=urlsplit(origin()).hostname,rp_name='Beschlussmanufaktur',user_name=user.email,user_id=bytes.fromhex(handle),challenge=challenge,authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,user_verification=UserVerificationRequirement.REQUIRED),exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k.credential_id)) for k in Passkey.objects.filter(user=user)])
            else:
                if purpose=='reauth':
                    if not request.user.is_authenticated:raise PermissionDenied
                    user=request.user;profile=AuthenticationProfile.objects.filter(user=user).first()
                # Discoverable passkey; no account existence or credential list exposed.
                result=generate_authentication_options(rp_id=urlsplit(origin()).hostname,challenge=challenge,user_verification=UserVerificationRequirement.REQUIRED)
            ceremony=WebAuthnCeremony.objects.create(user=user,purpose=purpose,challenge=bytes_to_base64url(challenge),session_digest=session_digest(request),expires_at=timezone.now()+timedelta(minutes=5),factor_version=profile.version if profile else 0,name=name)
            request.session['webauthn_ceremony']=str(ceremony.pk)
            response=json.loads(options_to_json(result));return JsonResponse(response)
    except (ValidationError,PermissionDenied,ValueError,TypeError,User.DoesNotExist):return JsonResponse({'error':'Sicherheitsprüfung fehlgeschlagen. Erneut anmelden oder Einstellungen prüfen.'},status=400)

@require_POST
def verify(request):
    try:
        if not consume_rate_limit('passkey-verify:'+client_address(request),20):raise PermissionDenied
        data=body(request)
        with transaction.atomic():
            ceremony=WebAuthnCeremony.objects.select_for_update().get(pk=request.session.get('webauthn_ceremony'))
            if ceremony.consumed_at or ceremony.expires_at<=timezone.now() or ceremony.session_digest!=session_digest(request):raise PermissionDenied
            ceremony.consumed_at=timezone.now();ceremony.save(update_fields=['consumed_at'])
            codes=[];user=None
            try:
                with transaction.atomic():
                    common={'expected_challenge':base64url_to_bytes(ceremony.challenge),'expected_rp_id':urlsplit(origin()).hostname,'expected_origin':origin(),'require_user_verification':True}
                    if ceremony.purpose=='register':
                        if not request.user.is_authenticated or request.user.pk!=ceremony.user_id:raise PermissionDenied
                        user=User.objects.select_for_update().get(pk=ceremony.user_id,is_active=True);profile=AuthenticationProfile.objects.select_for_update().get(user=user)
                        if profile.version!=ceremony.factor_version:raise PermissionDenied
                        if Passkey.objects.filter(user=user).count()>=10:raise ValidationError('Maximal zehn Passkeys.')
                        checked=verify_registration_response(credential=data,**common)
                        handle=Passkey.objects.filter(user=user).values_list('user_handle',flat=True).first()
                        # Handle issued in registration options is deterministically recovered from ceremony.
                        handle=request.session.get('webauthn_handle') if not handle else handle
                        if not handle:raise PermissionDenied
                        Passkey.objects.create(user=user,credential_id=bytes_to_base64url(checked.credential_id),public_key=checked.credential_public_key,user_handle=handle,sign_count=checked.sign_count,name=ceremony.name)
                        profile.method='passkey';profile.version+=1;codes=recovery(profile);profile.save();request.session['factor_version']=profile.version;request.session['authenticated_at']=int(time.time());request.session['passkey_reauthenticated_at']=int(time.time())
                        AuditEvent.objects.create(actor=user,action='authentication.passkey_registered');transaction.on_commit(lambda:notify_change(user))
                    else:
                        key=Passkey.objects.select_for_update().select_related('user').get(credential_id=data.get('id'))
                        user=User.objects.select_for_update().get(pk=key.user_id,is_active=True);profile=AuthenticationProfile.objects.select_for_update().get(user=user)
                        if ceremony.purpose=='reauth' and ceremony.user_id!=user.pk or ceremony.purpose=='login' and profile.method!='passkey':raise PermissionDenied
                        handle=data.get('response',{}).get('userHandle')
                        if not handle or base64url_to_bytes(handle)!=bytes.fromhex(key.user_handle):raise PermissionDenied
                        checked=verify_authentication_response(credential=data,credential_public_key=bytes(key.public_key),credential_current_sign_count=key.sign_count,**common)
                        key.sign_count=checked.new_sign_count;key.save(update_fields=['sign_count'])
                        authenticated(request,user);request.session['passkey_reauthenticated_at']=int(time.time());AuditEvent.objects.create(actor=user,action='authentication.passkey_verified')
            except Exception:
                # Persist single-use consumption even for a rejected response.
                return JsonResponse({'error':'Passkey konnte nicht bestätigt werden.'},status=400)
        request.session.pop('webauthn_ceremony',None);request.session.pop('webauthn_handle',None)
        return JsonResponse({'ok':True,'recovery':codes,'redirect':'/sicherheit/passkeys/' if ceremony.purpose=='register' else '/'})
    except (ValidationError,PermissionDenied,ValueError,TypeError,WebAuthnCeremony.DoesNotExist):return JsonResponse({'error':'Sicherheitsprüfung fehlgeschlagen.'},status=400)

@login_required
@require_POST
def remove(request,key_id):
    try:
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk,is_active=True);profile=confirmed(request,body(request));key=Passkey.objects.select_for_update().get(pk=key_id,user=request.user)
            if profile.method=='passkey' and Passkey.objects.filter(user=request.user).count()==1:raise ValidationError('Letzten Passkey erst nach bestätigtem Wechsel auf E-Mail/TOTP entfernen.')
            key.delete();profile.version+=1;profile.save(update_fields=['version']);request.session['factor_version']=profile.version;AuditEvent.objects.create(actor=request.user,action='authentication.passkey_removed');transaction.on_commit(lambda:notify_change(request.user))
        return JsonResponse({'ok':True})
    except (ValidationError,PermissionDenied,ValueError,TypeError,Passkey.DoesNotExist):return JsonResponse({'error':'Entfernung gesperrt. Faktor und aktuelle Anmeldung prüfen.'},status=400)
