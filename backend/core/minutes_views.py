from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods,require_GET
from .models import Meeting,Minutes,MinutesVersion
from .permissions import active_context
from .meetings_service import meeting_access
from .minutes_service import create,change
from .document_export import export
from .templates_service import render_markdown

@login_required
@require_http_methods(['GET','POST'])
def workspace(request,meeting_id):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'private',obj):raise PermissionDenied
    minutes=Minutes.objects.filter(meeting=obj).first();error=None;pending=None
    if request.method=='POST':
        try:
            action=request.POST.get('action')
            if action=='create':create(context,obj.pk,int(request.POST.get('meeting_version',0)))
            else:
                if not minutes:raise ValidationError('Noch keine Niederschrift.')
                pending={'markdown':request.POST.get('markdown',''),'public_markdown':request.POST.get('public_markdown',''),'kind':request.POST.get('kind','result')}
                change(context,minutes.pk,int(request.POST.get('version',0)),action,request.POST.get('reason',''),pending,request.POST.get('correction_meeting') or None)
        except (ValidationError,ValueError) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Fassung prüfen.'
        else:return redirect('minutes',meeting_id=obj.pk)
    editable=meeting_access(context,'protocol',obj) and request.user.pk in (obj.scribe_id,obj.chair_id)
    versions=minutes.versions.order_by('-version') if minutes else []
    chosen=versions.filter(version=request.GET.get('version')).first() if request.GET.get('version','').isdigit() else None
    shown=chosen.snapshot if chosen else pending if error and pending else {'markdown':minutes.markdown,'public_markdown':minutes.public_markdown,'kind':minutes.kind} if minutes else {}
    return render(request,'minutes.html',{'context':context,'obj':obj,'minutes':minutes,'editable':editable,'error':error,'shown':shown,'preview':mark_safe(render_markdown(shown.get('markdown',''))),'versions':versions,'chosen':chosen,'corrections':Meeting.objects.filter(committee=obj.committee,starts_at__gt=obj.starts_at)})

@login_required
@require_GET
def download(request,meeting_id,version,format):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'private',obj) or not meeting_access(context,'export',obj):raise PermissionDenied
    v=get_object_or_404(MinutesVersion,minutes__meeting=obj,version=version)
    if format not in ('pdf','docx'):raise Http404
    data,mime=export('Niederschrift · '+obj.title,v.snapshot['markdown'],format,subtitle=f'Fassung {v.version} · {v.snapshot["state"]}')
    response=HttpResponse(data,content_type=mime);response['Content-Disposition']=f'attachment; filename="niederschrift-{obj.pk}-{version}.{format}"';return response
