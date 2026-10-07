import difflib,json,uuid
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.http import Http404,JsonResponse,FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods,require_POST
from .models import Template,TemplateKind,TemplateVersion,TemplateParticipant,TemplateComment,Notification,Membership,Attachment,Consultation,RegistryRecord,TemplateLink,EditPresence,AuditEvent
from .permissions import active_context,available_contexts
from .templates_service import DEFAULT_KINDS,DEFAULT_TEXT,template_access,render_markdown,archive,touch,lock_template,validate_upload

class TemplateForm(forms.Form):
    subject=forms.CharField(label='Betreff',max_length=300)
    reference=forms.CharField(label='Aktenzeichen',max_length=200,required=False)
    classification=forms.ChoiceField(label='Empfängerkreis',choices=Template._meta.get_field('classification').choices)
    markdown=forms.CharField(label='Vorlagentext (Markdown)',max_length=100000,widget=forms.Textarea(attrs={'rows':20,'data-editor':'true'}))
    public_markdown=forms.CharField(label='Gesonderte öffentliche Textfassung',max_length=100000,required=False,widget=forms.Textarea(attrs={'rows':10,'data-editor':'true'}))
    unit=forms.ModelChoiceField(label='Zuständiger Fachbereich',queryset=RegistryRecord.objects.none(),required=False)
    expected_version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    reason=forms.CharField(label='Änderungsgrund',max_length=500)
    def __init__(self,*args,organization,kind,**kwargs):
        self.kind=kind
        super().__init__(*args,**kwargs)
        self.fields['unit'].queryset=RegistryRecord.objects.filter(organization=organization,kind='unit')
        for spec in kind.fields:
            name='extra_'+spec['key'];opts={'label':spec['label'],'required':spec.get('required',False),'initial':self.initial.get('fields',{}).get(spec['key'])}
            cls={'text':forms.CharField,'number':forms.DecimalField,'date':forms.DateField,'choice':forms.ChoiceField,'boolean':forms.BooleanField}.get(spec.get('type','text'))
            if cls==forms.CharField:opts['max_length']=4000
            if cls==forms.ChoiceField:opts['choices']=[(str(x),str(x)) for x in spec.get('choices',[])]
            if cls==forms.DateField:opts['widget']=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')
            self.fields[name]=cls(**opts)
    def field_values(self):
        return {spec['key']:self.cleaned_data['extra_'+spec['key']] if isinstance(self.cleaned_data['extra_'+spec['key']],(bool,int,float,type(None))) else str(self.cleaned_data['extra_'+spec['key']]) for spec in self.kind.fields}

@login_required
@require_http_methods(['GET'])
def index(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    query=request.GET.get('q','')[:100]
    candidates=Template.objects.select_related('kind','organization','author','unit').filter(subject__icontains=query)[:500]
    objects=[obj for obj in candidates if template_access(context,'read',obj)]
    return render(request,'templates_list.html',{'context':context,'objects':objects,'query':query,'can_create':context.role in ('author','clerk'),'notifications':Notification.objects.filter(user=request.user,read_at__isnull=True).order_by('-created_at')[:20]})

@login_required
@require_http_methods(['GET','POST'])
def edit(request,template_id=None):
    context=active_context(request)
    if not context:raise PermissionDenied
    obj=get_object_or_404(Template.objects.select_related('kind','organization','unit','author'),pk=template_id) if template_id else None
    if obj and not template_access(context,'edit',obj):raise PermissionDenied
    if not obj and context.role not in ('author','clerk'):raise PermissionDenied
    kinds=TemplateKind.objects.filter(organization=context.organization)
    selection=request.GET.get('kind') or request.POST.get('kind') or (str(obj.kind_id) if obj else '')
    try:kind=obj.kind if obj else kinds.filter(pk=selection).first() if selection and not selection.startswith('default:') else None
    except (ValueError,ValidationError):raise Http404
    if not kind:
        default=selection.removeprefix('default:') if selection else DEFAULT_KINDS[0]
        if default not in DEFAULT_KINDS:raise Http404
        kind=TemplateKind(organization=context.organization,name=default,initial_markdown=DEFAULT_TEXT)
        selection='default:'+default
    initial={name:getattr(obj,name) for name in ['subject','reference','classification','markdown','public_markdown','unit','fields']} if obj else {'markdown':kind.initial_markdown,'classification':'internal'}
    initial['expected_version']=obj.version if obj else 1
    form=TemplateForm(request.POST if request.method=='POST' else None,organization=context.organization,kind=kind,initial=initial)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                if obj:obj=lock_template(context,obj.pk,'edit',form.cleaned_data['expected_version'])
                else:
                    if not available_contexts(request.user).filter(pk=context.pk).exists():raise PermissionDenied
                    if kind._state.adding:kind,_=TemplateKind.objects.get_or_create(organization=context.organization,name=kind.name,defaults={'initial_markdown':kind.initial_markdown})
                    obj=Template(organization=context.organization,kind=kind,author=request.user)
                for name in ['subject','reference','classification','markdown','public_markdown','unit']:setattr(obj,name,form.cleaned_data[name])
                obj.fields=form.field_values();obj.full_clean()
                if template_id:touch(obj,request.user,form.cleaned_data['reason'])
                else:obj.save();archive(obj,request.user,form.cleaned_data['reason'])
        except ValidationError as e:form.add_error(None,ValidationError(e.messages))
        else:return redirect('template_detail',template_id=obj.pk)
    return render(request,'template_edit.html',{'context':context,'form':form,'obj':obj,'kind':kind,'selection':selection,'kinds':kinds,'default_kinds':DEFAULT_KINDS})

@login_required
@require_http_methods(['GET'])
def detail(request,template_id):
    context=active_context(request)
    obj=get_object_or_404(Template.objects.select_related('kind','organization','author','unit'),pk=template_id)
    if not template_access(context,'read',obj):raise PermissionDenied
    return render(request,'template_detail.html',{'context':context,'obj':obj,'body':mark_safe(render_markdown(obj.markdown)),'can_edit':template_access(context,'edit',obj),'can_delegate':template_access(context,'delegate',obj),'versions':obj.versions.order_by('-version'),'comments':obj.comments.select_related('author','task_assignee'),'attachments':obj.attachments.filter(removed_at__isnull=True),'presence':EditPresence.objects.filter(template=obj,seen_at__gte=timezone.now()-timezone.timedelta(seconds=90)).select_related('user'),'eligible':Membership.objects.filter(organization=obj.organization).select_related('user'),'consultations':obj.consultations.select_related('committee'),'committees':RegistryRecord.objects.filter(kind='committee',organization_id__in=available_contexts(request.user).values('organization_id'))})

@login_required
@require_POST
def preview(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    text=request.POST.get('markdown','')
    if len(text)>100000:return JsonResponse({'error':'too-large'},status=400)
    return JsonResponse({'html':render_markdown(text)})

@login_required
@require_POST
def heartbeat(request,template_id):
    context=active_context(request);obj=get_object_or_404(Template,pk=template_id)
    if not template_access(context,'edit',obj):raise PermissionDenied
    EditPresence.objects.update_or_create(template=obj,user=request.user,defaults={'seen_at':timezone.now()})
    return JsonResponse({'people':[p.user.get_full_name() or p.user.email for p in EditPresence.objects.filter(template=obj,seen_at__gte=timezone.now()-timezone.timedelta(seconds=90)).select_related('user')]})

@login_required
@require_http_methods(['GET'])
def compare(request,template_id,version):
    context=active_context(request);obj=get_object_or_404(Template,pk=template_id)
    if not template_access(context,'read',obj):raise PermissionDenied
    older=get_object_or_404(TemplateVersion,template=obj,version=version)
    diff='\n'.join(difflib.unified_diff(older.snapshot['markdown'].splitlines(),obj.markdown.splitlines(),fromfile=f'Version {version}',tofile=f'Version {obj.version}',lineterm=''))
    return render(request,'template_compare.html',{'context':context,'obj':obj,'older':older,'diff':diff})

@login_required
@require_POST
def upload(request,template_id):
    context=active_context(request)
    try:
        with transaction.atomic():
            obj=lock_template(context,template_id,'edit',int(request.POST.get('expected_version',0)))
            uploaded=request.FILES.get('file')
            if not uploaded:raise ValidationError('Datei fehlt.')
            name,media,digest=validate_upload(uploaded)
            # UUID storage names; original names never become filesystem paths.
            uploaded.name=str(uuid.uuid4())+'.bin'
            Attachment.objects.create(template=obj,name=name,file=uploaded,digest=digest,size=uploaded.size,media_type=media)
            touch(obj,request.user,'Anlage hinzugefügt (ungeprüft)')
    except (ValueError,ValidationError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=template_id)

@login_required
@require_http_methods(['GET'])
def download(request,attachment_id):
    context=active_context(request);a=get_object_or_404(Attachment.objects.select_related('template'),pk=attachment_id,removed_at__isnull=True)
    if not template_access(context,'export',a.template):raise PermissionDenied
    response=FileResponse(a.file.open('rb'),as_attachment=True,filename=a.name,content_type='application/octet-stream')
    response['X-Content-Type-Options']='nosniff';return response

@login_required
@require_POST
def attachment_change(request,attachment_id):
    context=active_context(request);a=get_object_or_404(Attachment,pk=attachment_id)
    try:
        with transaction.atomic():
            obj=lock_template(context,a.template_id,'edit',int(request.POST.get('expected_version',0)))
            a=Attachment.objects.select_for_update().get(pk=a.pk)
            if request.POST.get('action')=='remove':a.removed_at=timezone.now()
            else:a.checked=request.POST.get('checked')=='on';a.public=request.POST.get('public')=='on'
            a.save();touch(obj,request.user,'Anlagenstatus geändert')
    except (ValueError,ValidationError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=a.template_id)
