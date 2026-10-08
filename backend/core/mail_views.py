from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import MailReceipt,AuditEvent
from .user_views import admin_context
from .invitations import lock_admin
@login_required
@require_http_methods(['GET','POST'])
def inbox(request):
    context=admin_context(request)
    if request.method=='POST':
        with transaction.atomic():
            lock_admin(request.user,context.pk,context.organization_id)
            obj=get_object_or_404(MailReceipt,pk=request.POST.get('receipt'),organization=context.organization)
            obj.reviewed_at=timezone.now();obj.reviewed_by=request.user;obj.save(update_fields=['reviewed_at','reviewed_by'])
            AuditEvent.objects.create(actor=request.user,action='mail.reviewed',object_id=str(obj.pk))
        return redirect('mail_inbox')
    from django.core.paginator import Paginator
    return render(request,'mail_inbox.html',{'context':context,'receipts':Paginator(MailReceipt.objects.filter(organization=context.organization).order_by('-received_at'),20).get_page(request.GET.get('page'))})
