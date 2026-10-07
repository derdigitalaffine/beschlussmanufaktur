from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Meeting,Template,ExternalDocument,WorkspaceEntry,PersonalNote,Notification
from .permissions import active_context,available_contexts
from .meetings_service import meeting_access
from .templates_service import template_access,render_markdown

def resources(context,query=''):
    if not context or not available_contexts(context.user).filter(pk=context.pk).exists():raise PermissionDenied
    text=query.casefold();rows=[]
    for obj in Meeting.objects.select_related('committee').filter(organization=context.organization):
        if meeting_access(context,'read',obj) and text in (obj.title+' '+obj.committee.name+' '+obj.location).casefold():rows.append({'id':obj.pk,'kind':'meeting','title':obj.title,'subtitle':str(obj.starts_at)+' · '+obj.committee.name,'url':f'/sitzungen/{obj.pk}/'})
    if settings.SERVER_ROLE=='internal':
        for obj in Template.objects.select_related('organization','kind','author','unit').all():
            if template_access(context,'read',obj) and text in (obj.subject+' '+obj.number+' '+obj.markdown).casefold():rows.append({'id':obj.pk,'kind':'template','title':obj.subject,'subtitle':obj.number,'url':f'/vorlagen/{obj.pk}/'})
    else:
        for obj in ExternalDocument.objects.all():
            if 'read' in obj.permissions.get(str(context.pk),[]) and text in (obj.title+' '+obj.number+' '+obj.markdown).casefold():rows.append({'id':obj.pk,'kind':'template','title':obj.title,'subtitle':obj.number,'url':f'/dokumente/{obj.pk}/'})
    return rows

@login_required
@require_http_methods(['GET','POST'])
def desk(request):
    context=active_context(request);query=request.GET.get('q','')[:100];rows=resources(context,query)
    if request.method=='POST':
        # Recompute permission independent of a filtered search.
        target=next((row for row in resources(context) if row['kind']==request.POST.get('kind') and str(row['id'])==request.POST.get('resource_id')),None)
        if not target:raise PermissionDenied
        entry,_=WorkspaceEntry.objects.get_or_create(owner=request.user,context=context,kind=target['kind'],resource_id=target['id'])
        entry.favorite=not entry.favorite;entry.save(update_fields=['favorite']);return redirect('member_desk')
    entries={(entry.kind,entry.resource_id):entry for entry in WorkspaceEntry.objects.filter(owner=request.user,context=context)}
    for row in rows:row['favorite']=bool(entries.get((row['kind'],row['id'])) and entries[(row['kind'],row['id'])].favorite);row['viewed_at']=entries.get((row['kind'],row['id'])).viewed_at if (row['kind'],row['id']) in entries else None
    favorites=[row for row in rows if row['favorite']];recent=sorted([row for row in rows if row['viewed_at']],key=lambda row:row['viewed_at'],reverse=True)[:8]
    return render(request,'member_desk.html',{'context':context,'objects':rows,'favorites':favorites,'recent':recent,'query':query,'notifications':Notification.objects.filter(user=request.user,read_at__isnull=True).order_by('-created_at')[:20]})

@transaction.atomic
def save_note(context,meeting_id,version,text):
    obj=Meeting.objects.get(pk=meeting_id)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    if not isinstance(text,str) or len(text)>100000:raise ValidationError('Notiz zu groß.')
    # Lock the owner to serialize initial creation as well as updates.
    from .models import User
    User.objects.select_for_update().get(pk=context.user_id)
    note=PersonalNote.objects.select_for_update().filter(owner=context.user,context=context,meeting=obj).first()
    if not note:
        if version!=0:raise ValidationError('Notizstand geändert.')
        return PersonalNote.objects.create(owner=context.user,context=context,meeting=obj,markdown=text)
    if note.version!=version:raise ValidationError('Notiz wurde auf einem anderen Gerät geändert; lokalen Text vergleichen.')
    note.markdown=text;note.version+=1;note.save();return note

@login_required
@require_http_methods(['GET','POST'])
def note(request,meeting_id):
    context=active_context(request);obj=get_object_or_404(Meeting,pk=meeting_id)
    if not meeting_access(context,'read',obj):raise PermissionDenied
    personal=PersonalNote.objects.filter(owner=request.user,context=context,meeting=obj).first();error=None;text=personal.markdown if personal else ''
    if request.method=='POST':
        text=request.POST.get('markdown','')
        try:save_note(context,obj.pk,int(request.POST.get('version',0)),text)
        except (ValidationError,ValueError) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Stand prüfen.'
        else:return redirect('personal_note',meeting_id=obj.pk)
    WorkspaceEntry.objects.update_or_create(owner=request.user,context=context,kind='meeting',resource_id=obj.pk,defaults={'viewed_at':timezone.now()})
    return render(request,'personal_note.html',{'context':context,'obj':obj,'version':personal.version if personal else 0,'text':text,'preview':mark_safe(render_markdown(text)),'error':error})
