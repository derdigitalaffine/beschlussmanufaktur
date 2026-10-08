import hashlib,hmac,json,os,secrets,time,ssl
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPSHandler,HTTPRedirectHandler,ProxyHandler
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import TLSPlan,PortalConfiguration,AuditEvent,SystemOperator
from .operators import require_operator
from .secret_store import encrypt,decrypt
from .tls_material import hostname,certificate,dns_preflight

class PlanForm(forms.Form):
    role=forms.ChoiceField(label='Dienst',choices=[('internal','Internes Fachsystem'),('protected','Geschützter Arbeitsplatz'),('public','Bürgerportal')])
    hostname=forms.CharField(label='Konfigurierter Domainname',max_length=253)
    mode=forms.ChoiceField(label='TLS-Verfahren',choices=[('internal','Lokale Caddy-CA'),('letsencrypt',"Let's Encrypt (HTTP-/TLS-Challenge)"),('import','Eigenes Zertifikat importieren')])
    contact=forms.EmailField(label='ACME-Kontakt-E-Mail',required=False)
    expected_ips=forms.CharField(label='Erwartete öffentliche IPv4/IPv6-Adressen (Komma)',required=False)
    certificate_file=forms.FileField(label='PEM-Zertifikatskette',required=False)
    key_file=forms.FileField(label='Passender unverschlüsselter PEM-Schlüssel',required=False)
    reason=forms.CharField(label='Änderungsgrund',max_length=500)
    def clean(self):
        data=super().clean()
        try:
            host=hostname(data.get('hostname','').lower());data['hostname']=host
            origins={'internal':settings.APPLICATION_URL,'protected':settings.EXCHANGE_PROTECTED_URL,'public':settings.EXCHANGE_PUBLIC_URL}
            allowed={urlsplit(origins.get(data.get('role'),'')).hostname}
            if data.get('role')=='public':allowed.update(h for p in PortalConfiguration.objects.all() for h in p.domains)
            if host not in allowed:raise ValueError('Domain zuerst im Dienst-Origin oder Bürgerportal konfigurieren.')
            data['expected_ips']=[x.strip() for x in data.get('expected_ips','').split(',') if x.strip()]
            material={}
            if data.get('mode')=='import':
                if not data.get('certificate_file') or not data.get('key_file'):raise ValueError('Zertifikat und Schlüssel benötigt.')
                for field,key,limit in [('certificate_file','certificate',150000),('key_file','private_key',20000)]:
                    if data[field].size>limit:raise ValueError('Datei zu groß.')
                    material[key]=data[field].read().decode()
                data['certificate_info']=certificate(material['certificate'],material['private_key'],host)
                data['encrypted_material']=encrypt(json.dumps(material))
            elif data.get('certificate_file') or data.get('key_file'):raise ValueError('Schlüsseldateien nur beim Zertifikatimport.')
            if data.get('mode')=='letsencrypt' and (not data.get('contact') or not data['expected_ips']):raise ValueError('ACME-Kontakt und öffentliche Zieladressen erforderlich.')
        except (ValueError,TypeError,UnicodeError) as exc:raise ValidationError(str(exc))
        return data

@login_required
@require_http_methods(['GET','POST'])
def workspace(request):
    require_operator(request);form=PlanForm(request.POST or None,request.FILES or None);error=''
    if request.method=='POST':
        try:
            if request.POST.get('operation') in ('dns','apply'):
                obj=get_object_or_404(TLSPlan,pk=request.POST.get('plan'),operator=request.user)
                if request.POST['operation']=='dns':
                    dns_preflight(obj.hostname,obj.proof,obj.expected_ips);obj.dns_verified_at=timezone.now();obj.error='';obj.save(update_fields=['dns_verified_at','error'])
                else:
                    if obj.mode=='letsencrypt' and (not obj.dns_verified_at or obj.dns_verified_at<timezone.now()-timezone.timedelta(minutes=20)):raise ValidationError('Aktuelle erfolgreiche DNS-Prüfung erforderlich.')
                    obj.state='queued';obj.attempts=0;obj.apply_requested_at=timezone.now();obj.save(update_fields=['state','attempts','apply_requested_at']);AuditEvent.objects.create(actor=request.user,action='tls.apply_requested',object_id=str(obj.pk))
                return redirect('tls_management')
            if form.is_valid():
                data=form.cleaned_data;obj=TLSPlan.objects.create(operator=request.user,role=data['role'],hostname=data['hostname'],mode=data['mode'],proof=secrets.token_urlsafe(24),expected_ips=data['expected_ips'],contact=data['contact'],encrypted_material=data.get('encrypted_material',''),certificate_info=data.get('certificate_info',{}));AuditEvent.objects.create(actor=request.user,action='tls.prepared',object_id=str(obj.pk),metadata={'reason':data['reason'],'hostname':obj.hostname,'mode':obj.mode});return redirect('tls_management')
        except Exception:error='Prüfung fehlgeschlagen. DNS, Zertifikatsmaterial und Laufzeitkonfiguration prüfen. Es wurde keine TLS-Umstellung vorgenommen.'
    return render(request,'tls_management.html',{'form':form,'error':error,'plans':TLSPlan.objects.order_by('-created_at')[:30]})

def apply_pending():
    for obj in TLSPlan.objects.filter(state='queued').order_by('created_at')[:10]:
        if not SystemOperator.objects.filter(user=obj.operator,enabled=True).exists():obj.state='rejected';obj.error='Betriebsrolle beendet.';obj.save();continue
        if not obj.apply_requested_at or obj.apply_requested_at<timezone.now()-timezone.timedelta(minutes=20):obj.state='expired';obj.error='Auftrag abgelaufen; bewusst neu anfordern.';obj.save();continue
        obj.attempts+=1
        key=os.environ.get('TLS_INTERNAL_AGENT_KEY' if obj.role=='internal' else 'TLS_EXTERNAL_AGENT_KEY','')
        origin=os.environ.get('TLS_INTERNAL_AGENT_URL','http://tls-agent:8070') if obj.role=='internal' else settings.EXCHANGE_PUBLIC_URL+'/betrieb/tls-agent'
        try:
            if len(key)<32:raise ValidationError('Agentenschlüssel fehlt.')
            if obj.mode=='letsencrypt':dns_preflight(obj.hostname,obj.proof,obj.expected_ips)
            material=json.loads(decrypt(obj.encrypted_material)) if obj.encrypted_material else {}
            data={'id':str(obj.pk),'issued_at':int(time.time()),'role':obj.role,'hostname':obj.hostname,'mode':obj.mode,'proof':obj.proof,'expected_ips':obj.expected_ips,'contact':obj.contact,'certificate':material.get('certificate',''),'private_key':material.get('private_key','')}
            raw=json.dumps(data,sort_keys=True).encode()
            context=ssl.create_default_context()
            if settings.EXCHANGE_CA_FILE:context.load_verify_locations(settings.EXCHANGE_CA_FILE)
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs):raise ValueError('Umleitung nicht zugelassen.')
            if obj.role!='internal' and urlsplit(origin).scheme!='https':raise ValueError('HTTPS erforderlich.')
            opener=build_opener(NoRedirect(),HTTPSHandler(context=context),ProxyHandler({}))
            with opener.open(Request(origin+'/plan',data=raw,headers={'Content-Type':'application/json','X-BM-TLS-Signature':hmac.new(key.encode(),raw,hashlib.sha256).hexdigest()}),timeout=25) as response:
                result=json.loads(response.read(4096))
            if result!={'status':'applied','id':str(obj.pk)}:raise ValueError('Unbestätigter Auftrag.')
        except Exception:
            obj.error='Agent/DNS/TLS-Prüfung fehlgeschlagen; letzter gültiger Stand bleibt aktiv.'
            if obj.attempts>=10:obj.state='failed'
        else:obj.state='applied';obj.applied_at=timezone.now();obj.error='';AuditEvent.objects.create(actor=obj.operator,action='tls.applied',object_id=str(obj.pk),metadata={'hostname':obj.hostname,'mode':obj.mode})
        obj.save(update_fields=['state','applied_at','error','attempts'])
