from django.db import transaction
from django.db.models import Q,F
from django.core.exceptions import ValidationError,PermissionDenied
from .models import PersonIdentity,PersonProfile,Organization,AuditEvent
from .permissions import available_contexts

def visible(user):
    orgs=available_contexts(user).filter(role='organization_admin').values('organization_id')
    return PersonIdentity.objects.filter(Q(personprofile__organization_id__in=orgs)|Q(user__memberships__organization_id__in=orgs)).distinct()

def assign(profile):
    if profile.identity_id:
        if profile.user_id and profile.identity.user_id!=profile.user_id:raise ValidationError('Identität und Konto widersprechen sich.')
        return
    if profile.user_id:profile.identity,_=PersonIdentity.objects.get_or_create(user_id=profile.user_id,defaults={'name':profile.name})
    else:profile.identity=PersonIdentity.objects.create(name=profile.name)

@transaction.atomic
def merge(actor,source_id,target_id,reason):
    if source_id==target_id or not reason.strip() or len(reason)>500:raise ValidationError('Zwei unterschiedliche Identitäten und Begründung erforderlich.')
    owned=set(available_contexts(actor).filter(role='organization_admin').values_list('organization_id',flat=True))
    # Neither identity can be inspected or mutated outside explicit responsibilities.
    if not visible(actor).filter(pk=source_id).exists() or not visible(actor).filter(pk=target_id).exists():raise PermissionDenied
    orgs=set(PersonProfile.objects.filter(identity_id__in=[source_id,target_id]).values_list('organization_id',flat=True))
    if not orgs<=owned:raise PermissionDenied('Zusammenführung benötigt Verantwortung für alle beteiligten Körperschaften.')
    list(Organization.objects.select_for_update().filter(pk__in=orgs).order_by('id'))
    identities={p.pk:p for p in PersonIdentity.objects.select_for_update().filter(pk__in=[source_id,target_id])}
    source,target=identities[source_id],identities[target_id]
    if source.user_id and target.user_id and source.user_id!=target.user_id:raise ValidationError('Verschiedene Konten nicht automatisch zusammenführen.')
    if PersonProfile.objects.filter(identity=source,organization_id__in=PersonProfile.objects.filter(identity=target).values('organization_id')).exists():raise ValidationError('Beide Profile in derselben Körperschaft: fachliche Daten zunächst manuell bereinigen.')
    # Preserve source account when the selected target has none.
    account=source.user_id or target.user_id
    PersonProfile.objects.filter(identity=source).update(identity=target,version=F('version')+1)
    source.delete();target.user_id=account;target.save(update_fields=['user'])
    AuditEvent.objects.create(actor=actor,action='person_identity.merged',object_id=str(target.pk),metadata={'source':str(source_id),'reason':reason})

from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.views.decorators.http import require_http_methods
from .user_views import admin_context
class MergeForm(forms.Form):
    source=forms.ModelChoiceField(label='Doppelte Identität',queryset=PersonIdentity.objects.none())
    target=forms.ModelChoiceField(label='Beizubehaltende Identität',queryset=PersonIdentity.objects.none())
    reason=forms.CharField(label='Begründung und geprüfte Identität',max_length=500)
    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['source'].queryset=visible(user);self.fields['target'].queryset=visible(user)
@login_required
@require_http_methods(['GET','POST'])
def workspace(request):
    context=admin_context(request);form=MergeForm(request.POST or None,user=request.user)
    if request.method=='POST' and form.is_valid():
        try:merge(request.user,form.cleaned_data['source'].pk,form.cleaned_data['target'].pk,form.cleaned_data['reason'])
        except ValidationError as error:form.add_error(None,error)
        else:return redirect('person_identities')
    return render(request,'admin_form.html',{'context':context,'form':form,'title':'Zentrale Personen und Dubletten','description':'Konten bleiben eindeutig. Funktionen und öffentliche Freigaben bleiben je Körperschaft getrennt. Zusammenführen benötigt Verwaltungsrechte in allen beteiligten Körperschaften.','button':'Geprüfte Identitäten zusammenführen'})
