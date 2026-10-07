from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.shortcuts import get_object_or_404,render,redirect
from django.views.decorators.http import require_http_methods
from .models import Meeting,SessionReturn
from .permissions import active_context
from .meetings_service import meeting_access
from .session_transfer import prepare_return,accept
@login_required
@require_http_methods(['GET','POST'])
def returns(request,meeting_id):
    obj=get_object_or_404(Meeting,pk=meeting_id);context=active_context(request)
    if not meeting_access(context,'protocol',obj):raise PermissionDenied
    error=None
    if request.method=='POST':
        try:
            if settings.SERVER_ROLE=='protected':prepare_return(context,obj,int(request.POST.get('expected_version',0)))
            else:
                change=get_object_or_404(SessionReturn,pk=request.POST.get('return_id'),meeting=obj)
                accept(context,change.pk,request.POST.get('reason',''))
        except (ValidationError,ValueError) as e:error=' '.join(e.messages) if isinstance(e,ValidationError) else 'Stand prüfen.'
        else:return redirect('session_returns',meeting_id=obj.pk)
    return render(request,'session_returns.html',{'context':context,'obj':obj,'returns':obj.returns.all(),'external':settings.SERVER_ROLE=='protected','error':error})
