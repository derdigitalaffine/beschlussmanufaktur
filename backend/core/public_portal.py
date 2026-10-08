"""Read-only queries over the positive public projection."""
import uuid
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_GET
from .models import PublicRecord
from .templates_service import render_markdown

def validate_metadata(value, kind):
    if not isinstance(value,dict) or set(value)-{'starts_at','ends_at','location','committee_id'}:raise ValidationError('Unzulässige öffentliche Metadaten.')
    if value and (kind!='meeting' or set(value)!={'starts_at','ends_at','location','committee_id'}):raise ValidationError('Unvollständige Terminmetadaten.')
    if value:
        try:
            start,end=parse_datetime(value['starts_at']),parse_datetime(value['ends_at']);uuid.UUID(value['committee_id'])
            if not start or not end or start.utcoffset() is None or end.utcoffset() is None or end<=start:raise ValueError
            if not isinstance(value['location'],str) or len(value['location'])>1000:raise ValueError
        except (TypeError,ValueError):raise ValidationError('Ungültige Terminmetadaten.')

def selection(request):
    records=PublicRecord.objects.all()
    from .portal_configuration import for_request
    portal=for_request(request)
    if portal:records=records.filter(organization_id__in=portal.organizations)
    query=request.GET.get('q','').strip()[:200]
    if query:records=records.filter(Q(title__icontains=query)|Q(body__icontains=query))
    for key,field in [('organisation','organization_id'),('gremium','metadata__committee_id')]:
        if request.GET.get(key):
            try:value=str(uuid.UUID(request.GET[key]))
            except (ValueError,TypeError):return records.none()
            records=records.filter(**{field:value})
    kind=request.GET.get('art','')
    if kind:records=records.filter(kind=kind) if kind in ('meeting','template','minutes','committee','organization') else records.none()
    for key,lookup in [('von','gte'),('bis','lte')]:
        if request.GET.get(key):
            try:day=parse_date(request.GET[key])
            except ValueError:day=None
            if not day:return records.none()
            from django.utils import timezone
            matches=[]
            for obj in records.filter(kind='meeting').only('id','metadata'):
                dt=parse_datetime(obj.metadata.get('starts_at',''))
                if dt and ((timezone.localtime(dt).date()>=day) if lookup=='gte' else (timezone.localtime(dt).date()<=day)):matches.append(obj.pk)
            records=records.filter(pk__in=matches)
    return records.order_by('kind','metadata__starts_at','title','id')

@require_GET
def index(request):
    page=Paginator(selection(request),20).get_page(request.GET.get('page'));query=request.GET.copy();query.pop('page',None)
    return render(request,'public.html',{'page':page,'filters':request.GET,'query_string':query.urlencode(),'organizations':selection(request).filter(kind='organization'),'committees':selection(request).filter(kind='committee')})

@require_GET
def detail(request,record_id):
    obj=get_object_or_404(selection(request),pk=record_id)
    return render(request,'public_detail.html',{'record':obj,'body':render_markdown(obj.body)})

@require_GET
def calendar_feed(request):
    from .invitation_packets import calendar
    events=[]
    for obj in selection(request).filter(kind='meeting')[:1000]:
        if obj.metadata:events.extend(calendar({'id':str(obj.pk),'title':obj.title,**obj.metadata}).decode().split('\r\n')[3:-2])
    response=HttpResponse('\r\n'.join(['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Beschlussmanufaktur//Bürgerkalender//DE',*events,'END:VCALENDAR','']),content_type='text/calendar; charset=utf-8');response['Content-Disposition']='attachment; filename="sitzungen.ics"';return response

@require_GET
def api(request):
    page=Paginator(selection(request),100).get_page(request.GET.get('page'))
    return JsonResponse({'schema':'bm-public-v1','page':page.number,'pages':page.paginator.num_pages,'total':page.paginator.count,'results':[{'id':str(o.pk),'organization_id':str(o.organization_id),'kind':o.kind,'title':o.title,'markdown':o.body,'version':o.version,'metadata':o.metadata,'url':request.build_absolute_uri('/informationen/'+str(o.pk)+'/')} for o in page]})
