from django.conf import settings
from django.core.exceptions import PermissionDenied
from .models import SystemOperator

def require_operator(request):
    if settings.SERVER_ROLE!='internal' or not request.user.is_authenticated or not SystemOperator.objects.filter(user=request.user,enabled=True).exists():raise PermissionDenied('Ausdrückliche technische Betriebsrolle erforderlich.')
    import time
    if time.time()-request.session.get('authenticated_at',0)>600:raise PermissionDenied('Betriebsaktionen benötigen eine frische vollständige Anmeldung.')
