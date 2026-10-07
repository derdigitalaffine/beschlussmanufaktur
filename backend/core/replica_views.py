import io
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse,FileResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods
from .models import ExternalDocument,ReplicaAsset,PublicRecord,RemoteChange
from .permissions import active_context,available_contexts
from .templates_service import render_markdown
from .document_export import export

def document_access(request,obj,action):
    context=active_context(request)
    return bool(context and action in obj.permissions.get(str(context.pk),[]) and available_contexts(request.user).filter(pk=context.pk).exists())

@login_required
@require_http_methods(['GET'])
def documents(request):
    context=active_context(request)
    if not context:raise PermissionDenied
    query=request.GET.get('q','')[:100]
    objects=[obj for obj in ExternalDocument.objects.filter(title__icontains=query) if document_access(request,obj,'read')]
    return render(request,'replica_documents.html',{'context':context,'objects':objects,'query':query})

@login_required
@require_http_methods(['GET'])
def document(request,document_id):
    obj=get_object_or_404(ExternalDocument,pk=document_id)
    if not document_access(request,obj,'read'):raise PermissionDenied
    return render(request,'replica_document.html',{'context':active_context(request),'obj':obj,'body':mark_safe(render_markdown(obj.markdown)),'can_edit':document_access(request,obj,'edit')})

@login_required
@require_http_methods(['GET','POST'])
def propose_document(request,document_id):
    obj=get_object_or_404(ExternalDocument,pk=document_id)
    if not document_access(request,obj,'edit'):raise PermissionDenied
    class Form(forms.Form):
        content=forms.CharField(label='Änderungsvorschlag (Markdown)',max_length=100000,widget=forms.Textarea)
        reason=forms.CharField(label='Begründung',max_length=500)
        version=forms.IntegerField(widget=forms.HiddenInput,min_value=1)
    form=Form(request.POST if request.method=='POST' else None,initial={'content':obj.markdown,'version':obj.version})
    if request.method=='POST' and form.is_valid():
        RemoteChange.objects.create(organization_id=obj.organization_id,resource_id=obj.pk,resource_kind='template',context_id=active_context(request).pk,actor_id=request.user.pk,base_version=form.cleaned_data['version'],content=form.cleaned_data['content'],reason=form.cleaned_data['reason'])
        messages.success(request,'Vorschlag wartet auf interne Abholung und Prüfung.');return redirect('replica_document',document_id=obj.pk)
    return render(request,'registry_form.html',{'context':active_context(request),'form':form,'title':'Vorlagenänderung vorschlagen'})

@require_http_methods(['GET'])
def asset(request,document_id,asset_id):
    if settings.SERVER_ROLE=='public':
        obj=get_object_or_404(PublicRecord,pk=document_id)
    else:
        obj=get_object_or_404(ExternalDocument,pk=document_id)
        if not request.user.is_authenticated or not document_access(request,obj,'export'):raise PermissionDenied
    meta=next((a for a in obj.attachments if a['id']==str(asset_id)),None)
    if not meta:raise Http404
    binary=get_object_or_404(ReplicaAsset,pk=asset_id,digest=meta['digest'])
    return FileResponse(io.BytesIO(bytes(binary.data)),as_attachment=True,filename=meta['name'],content_type='application/octet-stream')

@require_http_methods(['GET'])
def document_export(request,document_id,format):
    if format not in ('pdf','docx'):raise Http404
    if settings.SERVER_ROLE=='public':
        obj=get_object_or_404(PublicRecord,pk=document_id);title=obj.title;text=obj.body
    else:
        obj=get_object_or_404(ExternalDocument,pk=document_id)
        if not request.user.is_authenticated or not document_access(request,obj,'export'):raise PermissionDenied
        title=obj.title;text=obj.markdown
    data,mime=export(title,text,format,subtitle=f'Version {obj.version}',metadata=[a['name'] for a in obj.attachments])
    response=HttpResponse(data,content_type=mime);response['Content-Disposition']=f'attachment; filename="vorlage-{obj.pk}.{format}"';return response
