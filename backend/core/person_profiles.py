import base64,io
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_GET,require_http_methods
from PIL import Image,ImageOps
from .models import PersonProfile,PublicRecord,AuditEvent,User
from .user_views import admin_context
from .invitations import lock_admin
from .public_portal import selection

PUBLIC_FIELDS=[('name','Name'),('function','Funktion'),('faction','Fraktion'),('starts_on','Amtszeitbeginn'),('ends_on','Amtszeitende'),('contact','Kontakt'),('photo','Foto')]

def sanitize_photo(upload):
    if upload.size>2*1024*1024:raise ValidationError('Foto maximal 2 MiB.')
    try:
        with Image.open(upload) as image:
            if image.width*image.height>16_000_000:raise ValueError
            image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((600,600));buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=80)
            return base64.b64encode(buffer.getvalue()).decode()
    except (OSError,ValueError,Image.DecompressionBombError):raise ValidationError('Foto kann nicht sicher verarbeitet werden.')

def projection(obj):
    allowed={k for k,_ in PUBLIC_FIELDS};fields=set(obj.public_fields)&allowed
    # Account email and internal identity references are never projected.
    values={k:(getattr(obj,k).isoformat() if getattr(obj,k) and k.endswith('_on') else getattr(obj,k)) for k in fields}
    title=values.get('name') or 'Gremienmitglied'
    text='\n\n'.join(label+': '+str(values[k]) for k,label in PUBLIC_FIELDS if k in values and k not in ('name','photo') and values[k])
    return {'id':str(obj.pk),'organization_id':str(obj.organization_id),'kind':'person','title':title,'body':text,'version':obj.version,'attachments':[],'metadata':values}

class ProfileForm(forms.ModelForm):
    public_fields=forms.MultipleChoiceField(label='Einzeln öffentlich freigegebene Felder',choices=PUBLIC_FIELDS,required=False,widget=forms.CheckboxSelectMultiple)
    portrait=forms.FileField(label='Foto (JPEG/PNG, max. 2 MiB)',required=False)
    remove_photo=forms.BooleanField(label='Foto entfernen',required=False)
    expected_version=forms.IntegerField(min_value=1,widget=forms.HiddenInput)
    reason=forms.CharField(label='Begründung der Änderung/Freigabe',max_length=500)
    class Meta:
        model=PersonProfile;fields=['identity','user','name','function','faction','starts_on','ends_on','contact','public_fields','published']
        labels={'identity':'Zentrale Person (vorhandene Identität auswählen)','user':'Zugehöriges Konto (optional)','name':'Name','function':'Funktion','faction':'Fraktion','starts_on':'Amtszeitbeginn','ends_on':'Amtszeitende','contact':'Freigebbarer Kontakt','published':'Ausgewählte Felder veröffentlichen'}
        widgets={k:forms.DateInput(attrs={'type':'date'}) for k in ('starts_on','ends_on')}
    def __init__(self,*args,context,**kwargs):
        super().__init__(*args,**kwargs)
        from .identities import visible
        self.fields['identity'].queryset=visible(context.user)
        self.fields['user'].queryset=User.objects.filter(memberships__organization=context.organization).distinct();self.initial['expected_version']=self.instance.version
    def clean(self):
        data=super().clean()
        if data.get('starts_on') and data.get('ends_on') and data['ends_on']<data['starts_on']:raise ValidationError('Amtszeitende liegt vor Beginn.')
        if data.get('portrait'):self.instance.photo=sanitize_photo(data['portrait'])
        if data.get('remove_photo'):self.instance.photo=''
        return data

@login_required
@require_http_methods(['GET','POST'])
def profiles(request,profile_id=None):
    context=admin_context(request);obj=get_object_or_404(PersonProfile,pk=profile_id,organization=context.organization) if profile_id else PersonProfile(organization=context.organization)
    form=ProfileForm(request.POST or None,request.FILES or None,instance=obj,context=context)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                lock_admin(request.user,context.pk,context.organization_id)
                current=PersonProfile.objects.filter(pk=obj.pk).first()
                if current and current.version!=form.cleaned_data['expected_version']:raise ValidationError('Parallel geändert. Neu laden.')
                obj=form.save(commit=False)
                from .identities import assign
                assign(obj)
                obj.version+=1;obj.full_clean();obj.save()
                AuditEvent.objects.create(actor=request.user,action='person_profile.saved',object_id=str(obj.pk),metadata={'public_fields':obj.public_fields,'published':obj.published,'reason':form.cleaned_data['reason']})
        except ValidationError as error:form.add_error(None,error)
        else:return redirect('person_profiles')
    return render(request,'person_profiles.html',{'form':form,'context':context,'profiles':PersonProfile.objects.filter(organization=context.organization).order_by('name')})

@require_GET
def portrait(request,record_id):
    obj=get_object_or_404(selection(request),pk=record_id,kind='person')
    value=obj.metadata.get('photo','')
    if not value:return HttpResponse(status=404)
    return HttpResponse(base64.b64decode(value,validate=True),content_type='image/jpeg')
