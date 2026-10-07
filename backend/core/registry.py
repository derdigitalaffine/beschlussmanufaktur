from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .models import AuditEvent, Membership, Organization, OrganizationRelation, RegistryRecord, Mandate
from .permissions import active_context, available_contexts
from .user_views import admin_context
from .invitations import lock_admin

class RecordForm(forms.ModelForm):
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    reason = forms.CharField(label='Begründung', max_length=500)
    class Meta:
        model = RegistryRecord
        fields = ['kind','name','starts_on','ends_on','details','archived']
        labels = {'kind':'Art','name':'Bezeichnung','starts_on':'Beginn','ends_on':'Ende','details':'Beschreibung','archived':'Historischer Datensatz'}
        widgets = {x:forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d') for x in ['starts_on','ends_on']}

class MandateForm(forms.ModelForm):
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    reason = forms.CharField(label='Begründung', max_length=500)
    class Meta:
        model = Mandate
        fields = ['committee','term','user','person','function','faction','substitutes_for','starts_on','ends_on','voting','archived']
        labels = {'committee':'Gremium','term':'Legislaturperiode','user':'Konto','person':'Person ohne Konto','function':'Funktion','faction':'Fraktion','substitutes_for':'Vertretung für','starts_on':'Individueller Amtsbeginn','ends_on':'Individuelles Amtsende','voting':'Stimmberechtigt','archived':'Historischer Datensatz'}
        widgets = {x:forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d') for x in ['starts_on','ends_on']}
    def __init__(self,*args,organization,**kwargs):
        super().__init__(*args,**kwargs)
        for name,kind in [('committee','committee'),('term','term'),('person','person'),('function','function'),('faction','faction')]:
            self.fields[name].queryset=RegistryRecord.objects.filter(organization=organization,kind=kind)
        from .models import User
        self.fields['user'].queryset = User.objects.filter(pk__in=Membership.objects.filter(organization=organization).values('user_id'))
        self.fields['substitutes_for'].queryset=Mandate.objects.filter(committee__organization=organization,substitutes_for__isnull=True)

class RelationForm(forms.ModelForm):
    class Meta:
        model = OrganizationRelation
        fields = ['target','description','starts_on','ends_on','responsibility']
        labels={'target':'Weitere Körperschaft','description':'Beziehung','starts_on':'Beginn','ends_on':'Ende','responsibility':'Verantwortliche Stelle'}
        widgets = {x:forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d') for x in ['starts_on','ends_on']}
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['target'].queryset=Organization.objects.filter(pk__in=available_contexts(user).values('organization_id'))
    def clean(self):
        data=super().clean()
        if data.get('starts_on') and data.get('ends_on') and data['ends_on']<data['starts_on']:
            raise ValidationError('Ungültiger Zeitraum.')
        return data

@login_required
@require_http_methods(['GET','POST'])
def index(request):
    context=admin_context(request)
    form=RelationForm(request.POST if request.method=='POST' else None,user=request.user)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                lock_admin(request.user,context.pk,context.organization_id)
                relation=form.save(commit=False);relation.source=context.organization
                relation.full_clean();relation.save()
                AuditEvent.objects.create(actor=request.user,action='organization.related',object_id=str(relation.pk))
        except ValidationError as e: form.add_error(None,e)
        else: return redirect('registry')
    records=RegistryRecord.objects.filter(organization=context.organization)
    return render(request,'registry.html',{'context':context,'records':records,'mandates':Mandate.objects.filter(committee__organization=context.organization).select_related('committee','function','user','person','faction','term'),'relations':context.organization.outgoing_relations.select_related('target'),'form':form,'tree':Organization.objects.filter(pk__in=available_contexts(request.user).values('organization_id')).select_related('primary_parent')})

@login_required
@require_http_methods(['GET','POST'])
def edit(request,kind,record_id=None):
    context=admin_context(request)
    if kind not in ('mandate','record'): raise Http404
    model=Mandate if kind=='mandate' else RegistryRecord
    query=model.objects.filter(**({'committee__organization':context.organization} if kind=='mandate' else {'organization':context.organization}))
    obj=get_object_or_404(query,pk=record_id) if record_id else model()
    if kind!='mandate':obj.organization=context.organization
    form_class=MandateForm if kind=='mandate' else RecordForm
    kwargs={'organization':context.organization} if kind=='mandate' else {}
    form=form_class(request.POST if request.method=='POST' else None,instance=obj,initial={'expected_version':obj.version},**kwargs)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                lock_admin(request.user,context.pk,context.organization_id)
                old=query.select_for_update().filter(pk=record_id).first() if record_id else None
                if old and old.version!=form.cleaned_data['expected_version']:
                    raise ValidationError('Zwischenzeitlich geändert. Bitte neu laden.')
                before = snapshot(old) if old else None
                saved=form.save(commit=False)
                saved.version=(old.version+1) if old else 1
                saved.full_clean();saved.save()
                AuditEvent.objects.create(actor=request.user,action='registry.saved',object_id=str(saved.pk),metadata={'organization':str(context.organization_id),'reason':form.cleaned_data['reason'],'version':saved.version,'before':before,'after':snapshot(saved)})
        except ValidationError as e:form.add_error(None,e)
        else:
            messages.success(request,'Stand gespeichert. Frühere Amtszeiten bitte als historische Datensätze erhalten.');return redirect('registry')
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Mandat / Fraktionszugehörigkeit' if kind=='mandate' else 'Stammdatensatz'})

@login_required
@require_POST
def mode(request):
    context=active_context(request)
    if not context: raise PermissionDenied
    request.user.advanced_mode=request.POST.get('mode')=='advanced' and context.organization.advanced_enabled
    request.user.save(update_fields=['advanced_mode'])
    return redirect('home')


def snapshot(obj):
    if not obj:return None
    return {field.name: str(getattr(obj,field.attname)) if getattr(obj,field.attname) is not None else None for field in obj._meta.fields}

class StructureForm(forms.ModelForm):
    expected_version = forms.CharField(widget=forms.HiddenInput)
    reason = forms.CharField(label='Begründung',max_length=500)
    class Meta:
        model=Organization
        fields=['name','kind','primary_parent','advanced_enabled']
        labels={'name':'Bezeichnung','kind':'Körperschaftstyp','primary_parent':'Hauptzuordnung','advanced_enabled':'Erweiterte Ansicht erlauben'}
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['primary_parent'].queryset=Organization.objects.filter(pk__in=available_contexts(user).filter(role='organization_admin').values('organization_id'))

@login_required
@require_http_methods(['GET','POST'])
def structure(request):
    context=admin_context(request)
    obj=context.organization
    # Compare the full structural snapshot; all tree writes serialize by UUID order.
    import hashlib,json
    def version(item):return hashlib.sha256(json.dumps(snapshot(item),sort_keys=True).encode()).hexdigest()
    form=StructureForm(request.POST if request.method=='POST' else None,user=request.user,instance=obj,initial={'expected_version':version(obj)})
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                list(Organization.objects.select_for_update().order_by('pk'))
                lock_admin(request.user,context.pk,context.organization_id)
                old=Organization.objects.get(pk=obj.pk)
                if version(old)!=form.cleaned_data['expected_version']:raise ValidationError('Struktur wurde geändert. Bitte neu laden.')
                saved=form.save(commit=False);saved.full_clean();saved.save()
                AuditEvent.objects.create(actor=request.user,action='organization.updated',object_id=str(saved.pk),metadata={'reason':form.cleaned_data['reason'],'before':snapshot(old),'after':snapshot(saved)})
        except ValidationError as e:form.add_error(None,e)
        else:return redirect('registry')
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Körperschaft und Hauptzuordnung'})
