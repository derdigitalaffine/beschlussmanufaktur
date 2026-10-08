import re,uuid
from urllib.parse import urlsplit
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect,render
from django.views.decorators.http import require_GET,require_http_methods
from .models import PortalConfiguration,Organization,AuditEvent
from .permissions import available_contexts
from .user_views import admin_context

FIELDS=['id','organization_id','title','introduction','color','domains','organizations','frame_origins','version']

def validate(obj):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',obj.color):raise ValidationError('Farbe als #RRGGBB angeben.')
    # White foreground must remain readable on the chosen primary color.
    rgb=[int(obj.color[i:i+2],16)/255 for i in (1,3,5)]
    luminance=sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(rgb,[.2126,.7152,.0722]))
    if 1.05/(luminance+.05)<4.5:raise ValidationError('Farbe benötigt mindestens 4,5:1 Kontrast zu Weiß.')
    for collection in (obj.domains,obj.organizations,obj.frame_origins):
        if not isinstance(collection,list) or len(collection)>40 or len(set(collection))!=len(collection):raise ValidationError('Ungültige oder doppelte Portalzuordnung.')
    for domain in obj.domains:
        if not isinstance(domain,str) or len(domain)>253 or domain!=domain.lower() or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',domain):raise ValidationError('Domain ohne Protokoll, Pfad oder Platzhalter angeben.')
    for identifier in obj.organizations:
        try:uuid.UUID(identifier)
        except (ValueError,TypeError):raise ValidationError('Ungültige Körperschaft.')
    for origin in obj.frame_origins:
        if not isinstance(origin,str):raise ValidationError('Ungültiger iframe-Origin.')
        u=urlsplit(origin)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.path or u.query or u.fragment or u.netloc!=u.hostname:raise ValidationError('iframe nur für vollständige HTTPS-Origins ohne Port freigeben.')
        if not re.fullmatch(r'[a-z0-9.-]+',u.hostname):raise ValidationError('Ungültiger iframe-Origin.')
    conflicts=PortalConfiguration.objects.exclude(pk=obj.pk)
    if any(set(other.domains)&set(obj.domains) for other in conflicts):raise ValidationError('Domain ist bereits einem anderen Portal zugeordnet.')


def for_request(request):
    if settings.SERVER_ROLE!='public' or request.path.startswith('/health/'):return None
    host=request.get_host().split(':')[0].lower()
    return next((p for p in PortalConfiguration.objects.all() if host in p.domains),None)


def context_processor(request):
    return {'portal':for_request(request)}

class PortalForm(forms.ModelForm):
    domains_text=forms.CharField(label='Eigene Domains (eine pro Zeile)',required=False,widget=forms.Textarea)
    frames_text=forms.CharField(label='Kommunale Webseiten für iframe (HTTPS-Origin pro Zeile)',required=False,widget=forms.Textarea)
    scope=forms.ModelMultipleChoiceField(label='Körperschaften im Portal',queryset=Organization.objects.none(),widget=forms.CheckboxSelectMultiple)
    expected_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    class Meta:
        model=PortalConfiguration;fields=['title','introduction','color'];labels={'title':'Portalname','introduction':'Einleitung','color':'Hauptfarbe (#RRGGBB)'}
    def __init__(self,*args,context,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['scope'].queryset=Organization.objects.filter(pk__in=available_contexts(context.user).filter(role='organization_admin').values('organization_id'))
        if not self.is_bound:self.initial.update(domains_text='\n'.join(self.instance.domains),frames_text='\n'.join(self.instance.frame_origins),scope=self.instance.organizations,expected_version=self.instance.version)
    def clean(self):
        cleaned=super().clean()
        self.instance.domains=[x.strip().lower() for x in cleaned.get('domains_text','').splitlines() if x.strip()]
        self.instance.frame_origins=[x.strip() for x in cleaned.get('frames_text','').splitlines() if x.strip()]
        self.instance.organizations=[str(x.pk) for x in cleaned.get('scope',[])]
        return cleaned

@login_required
@require_http_methods(['GET','POST'])
def configure(request):
    context=admin_context(request)
    obj=PortalConfiguration.objects.filter(organization_id=context.organization_id).first() or PortalConfiguration(organization_id=context.organization_id,organizations=[str(context.organization_id)])
    form=PortalForm(request.POST or None,instance=obj,context=context)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                Organization.objects.select_for_update().get(pk=context.organization_id)
                from .invitations import lock_admin
                lock_admin(request.user,context.pk,context.organization_id)
                current=PortalConfiguration.objects.filter(pk=obj.pk).first()
                if current and current.version!=form.cleaned_data['expected_version']:raise ValidationError('Parallel geändert. Neu laden.')
                obj=form.save(commit=False);obj.version+=1;obj.full_clean();obj.save()
                AuditEvent.objects.create(actor=request.user,action='portal.configured',object_id=str(obj.pk),metadata={'version':obj.version})
        except ValidationError as error:form.add_error(None,error)
        else:messages.success(request,'Portalkonfiguration gespeichert. Bereitstellung erfolgt mit dem nächsten öffentlichen Abgleich. Domainrouting/TLS muss zusätzlich eingerichtet werden.');return redirect('portal_configure')
    return render(request,'admin_form.html',{'form':form,'context':context,'title':'Bürgerportal und Erscheinungsbild','description':'Eigene Domains verwenden zentrale freigegebene Daten. Ohne Domainzuordnung bleibt das gemeinsame Portal bestehen.','button':'Speichern'})

@require_GET
def stylesheet(request):
    portal=for_request(request)
    color=portal.color if portal else '#245846'
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):color='#245846'
    return HttpResponse(':root{--green:'+color+'}',content_type='text/css')
