import json
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_POST
from .models import Template,TemplateKind,TemplateParticipant,TemplateComment,Membership,Consultation,RegistryRecord,TemplateLink,ReviewStep,Notification,AuditEvent
from .templates_service import lock_template,template_access,touch,notify
from .permissions import active_context,available_contexts
from .user_views import admin_context
from .invitations import lock_admin
from .workflow import submit,decide,publish,step_access
from .document_export import export

class KindForm(forms.ModelForm):
    class Meta:
        model=TemplateKind
        fields=['name','initial_markdown','fields','workflow','four_eyes']
        labels={'name':'Vorlagenart','initial_markdown':'Standardabschnitte (Markdown)','fields':'Zusatzfelder / Pflichtfelder (JSON)','workflow':'Prüfschritte / parallele Gruppen / Bedingungen (JSON)','four_eyes':'Vieraugenprinzip'}
        widgets={'fields':forms.Textarea(attrs={'rows':8}),'workflow':forms.Textarea(attrs={'rows':8})}

@login_required
@require_http_methods(['GET','POST'])
def kind(request,kind_id=None):
    context=admin_context(request)
    obj=get_object_or_404(TemplateKind,pk=kind_id,organization=context.organization) if kind_id else TemplateKind(organization=context.organization)
    form=KindForm(request.POST if request.method=='POST' else None,instance=obj)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            lock_admin(request.user,context.pk,context.organization_id)
            saved=form.save();AuditEvent.objects.create(actor=request.user,action='template.kind',object_id=str(saved.pk),metadata={'fields':saved.fields,'workflow':saved.workflow,'four_eyes':saved.four_eyes})
        return redirect('kind_list')
    return render(request,'kind_form.html',{'context':context,'form':form})

@login_required
@require_http_methods(['GET'])
def kind_list(request):
    context=admin_context(request)
    return render(request,'kind_list.html',{'context':context,'kinds':TemplateKind.objects.filter(organization=context.organization)})

@login_required
@require_POST
def action(request,template_id):
    context=active_context(request)
    try:
        version=int(request.POST.get('expected_version',0));verb=request.POST.get('action')
        if verb=='submit':submit(context,template_id,version)
        elif verb in ('publish','withdraw'):publish(context,template_id,version,withdraw=verb=='withdraw')
        else:raise ValidationError('Unbekannte Aktion.')
    except (ValidationError,ValueError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=template_id)

@login_required
@require_POST
def review(request,step_id):
    step=get_object_or_404(ReviewStep,pk=step_id)
    try:decide(active_context(request),step_id,int(request.POST.get('expected_version',0)),request.POST.get('decision'),request.POST.get('comment',''))
    except (ValidationError,ValueError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=step.template_id)

@login_required
@require_POST
def participant(request,template_id):
    context=active_context(request)
    with transaction.atomic():
        try:obj=lock_template(context,template_id,'delegate',int(request.POST.get('expected_version',0)))
        except (ValidationError,ValueError) as e:messages.error(request,str(e));return redirect('template_detail',template_id=template_id)
        member=get_object_or_404(Membership,pk=request.POST.get('membership'),organization=obj.organization)
        if not available_contexts(member.user).filter(pk=member.pk).exists():raise PermissionDenied
        actions=request.POST.getlist('rights')
        if set(actions)-{'read','edit','export','review','release'} or any(not template_access(context,a,obj) for a in actions):raise PermissionDenied('Nur eigene vergebbare Rechte können weitergegeben werden.')
        TemplateParticipant.objects.update_or_create(template=obj,membership=member,defaults={'actions':actions,'revoked_at':timezone.now() if not actions else None})
        AuditEvent.objects.create(actor=request.user,action='template.participation',object_id=str(obj.pk),metadata={'membership':str(member.pk),'actions':actions})
        if actions:Notification.objects.create(user=member.user,text='Sie wurden an einer Vorlage beteiligt.',path=f'/vorlagen/{obj.pk}/')
    return redirect('template_detail',template_id=template_id)

@login_required
@require_POST
def comment(request,template_id):
    context=active_context(request);obj=get_object_or_404(Template,pk=template_id)
    if not template_access(context,'read',obj):raise PermissionDenied
    text=request.POST.get('text','').strip()
    if not text or len(text)>4000:messages.error(request,'Kommentar benötigt Text bis 4000 Zeichen.');return redirect('template_detail',template_id=template_id)
    assignee=None
    if request.POST.get('assignee'):
        member=get_object_or_404(Membership,pk=request.POST['assignee'],organization=obj.organization)
        if not template_access(member,'read',obj):raise PermissionDenied('Aufgabenempfänger benötigt ein eigenes Leserecht.')
        assignee=member.user
    note=TemplateComment.objects.create(template=obj,author=request.user,text=text,version=obj.version,task_assignee=assignee)
    notify(obj,request.user)
    if assignee:Notification.objects.create(user=assignee,text='Eine Aufgabe wurde Ihnen zugewiesen.',path=f'/vorlagen/{obj.pk}/')
    return redirect('template_detail',template_id=template_id)

@login_required
@require_POST
def complete_task(request,comment_id):
    note=get_object_or_404(TemplateComment,pk=comment_id)
    context=active_context(request)
    if not template_access(context,'read',note.template) or not (note.task_assignee_id==request.user.pk or template_access(context,'edit',note.template)):raise PermissionDenied
    note.completed_at=timezone.now();note.save(update_fields=['completed_at'])
    return redirect('template_detail',template_id=note.template_id)

@login_required
@require_POST
def consultation(request,template_id):
    context=active_context(request)
    try:
        with transaction.atomic():
            obj=lock_template(context,template_id,'edit',int(request.POST.get('expected_version',0)))
            committee=get_object_or_404(RegistryRecord,pk=request.POST.get('committee'),kind='committee',archived=False)
            if committee.organization_id!=obj.organization_id and not available_contexts(request.user).filter(organization_id=committee.organization_id,role__in=['clerk','organization_admin']).exists():raise PermissionDenied('Zuständigkeit für die weitere Körperschaft erforderlich.')
            Consultation.objects.create(template=obj,committee=committee,position=int(request.POST.get('position',1)),deciding=request.POST.get('deciding')=='on',public=request.POST.get('public')=='on',may_amend=request.POST.get('may_amend')=='on')
            touch(obj,request.user,'Beratungsfolge erweitert')
    except (ValidationError,ValueError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=template_id)

@login_required
@require_http_methods(['GET','POST'])
def amendment(request,consultation_id):
    context=active_context(request);obj=get_object_or_404(Consultation.objects.select_related('template','committee'),pk=consultation_id)
    if not context or context.organization_id!=obj.committee.organization_id or not obj.may_amend or context.role not in ('clerk','chair') or not available_contexts(request.user).filter(pk=context.pk).exists():raise PermissionDenied
    class AmendmentForm(forms.Form):
        markdown=forms.CharField(label='Lokale Ergänzung (Markdown)',max_length=100000,widget=forms.Textarea)
        expected_version=forms.IntegerField(widget=forms.HiddenInput)
        reason=forms.CharField(label='Begründung',max_length=500)
    form=AmendmentForm(request.POST if request.method=='POST' else None,initial={'markdown':obj.amendment,'expected_version':obj.version})
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            target=Consultation.objects.select_for_update().get(pk=obj.pk)
            if target.version!=form.cleaned_data['expected_version']:form.add_error(None,'Lokale Ergänzung wurde geändert. Bitte neu laden.')
            else:
                target.amendment=form.cleaned_data['markdown'];target.version+=1;target.save()
                AuditEvent.objects.create(actor=request.user,action='consultation.amended',object_id=str(target.pk),metadata={'version':target.version,'text':target.amendment,'reason':form.cleaned_data['reason']})
                messages.success(request,'Lokale Ergänzung gespeichert. Die Ausgangsvorlage wurde nicht überschrieben.');return redirect('templates')
    return render(request,'registry_form.html',{'context':context,'form':form,'title':'Gremienbezogene Ergänzung'})

@login_required
@require_POST
def link(request,template_id):
    context=active_context(request)
    with transaction.atomic():
        try:obj=lock_template(context,template_id,'edit',int(request.POST.get('expected_version',0)))
        except (ValidationError,ValueError) as e:messages.error(request,str(e));return redirect('template_detail',template_id=template_id)
        other=get_object_or_404(Template,pk=request.POST.get('target'))
        if not template_access(context,'read',other):raise PermissionDenied
        if obj.pk==other.pk:raise PermissionDenied
        TemplateLink.objects.create(source=obj,target=other,description=request.POST.get('description','')[:200]);touch(obj,request.user,'Vorgangsverknüpfung ergänzt')
    return redirect('template_detail',template_id=template_id)

@login_required
@require_http_methods(['GET'])
def document(request,template_id,format,version=None):
    obj=get_object_or_404(Template,pk=template_id);context=active_context(request)
    if not template_access(context,'export',obj):raise PermissionDenied
    if format not in ('pdf','docx'):raise Http404
    archived=get_object_or_404(obj.versions,version=version or obj.version)
    data,mime=export(archived.snapshot['subject'],archived.snapshot['markdown'],format,subtitle=f'{obj.organization} · {obj.number or "Entwurf"} · Version {archived.version}',metadata=[a['name']+' · SHA-256 '+a['digest'] for a in archived.snapshot['attachments']])
    response=HttpResponse(data,content_type=mime);response['Content-Disposition']=f'attachment; filename="vorlage-{obj.pk}-v{archived.version}.{format}"';return response

@login_required
@require_POST
def notification_read(request,notification_id):
    n=get_object_or_404(Notification,pk=notification_id,user=request.user);n.read_at=timezone.now();n.save(update_fields=['read_at']);return redirect('templates')

@login_required
@require_POST
def add_step(request,template_id):
    context=active_context(request)
    try:
        with transaction.atomic():
            obj=lock_template(context,template_id,'edit',int(request.POST.get('expected_version',0)))
            if obj.state!='review':raise ValidationError('Manuelle Beteiligung benötigt einen laufenden Prüfstand.')
            member=get_object_or_404(Membership,pk=request.POST.get('membership'),organization=obj.organization,role__in=['reviewer','release','clerk'])
            if not available_contexts(member.user).filter(pk=member.pk).exists():raise PermissionDenied
            from django.db.models import Max
            group=obj.review_steps.filter(version=obj.version).aggregate(value=Max('group'))['value'] or 1
            name=request.POST.get('name','Zusätzliche Prüfung')[:100]
            ReviewStep.objects.create(template=obj,version=obj.version,name=name,role=member.role,assigned=member,group=group)
            AuditEvent.objects.create(actor=request.user,action='template.reviewer_added',object_id=str(obj.pk),metadata={'version':obj.version,'membership':str(member.pk),'name':name})
            Notification.objects.create(user=member.user,text='Eine zusätzliche Prüfung wurde Ihnen zugewiesen.',path=f'/vorlagen/{obj.pk}/')
    except (ValidationError,ValueError) as e:messages.error(request,str(e))
    return redirect('template_detail',template_id=template_id)
