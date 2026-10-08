from contextlib import contextmanager
from django.db import connection,transaction
from django.http import HttpResponse
from .models import OperationalState

LOCK=74812609
@contextmanager
def gate(exclusive=False):
    with transaction.atomic():
        if connection.vendor=='postgresql':
            with connection.cursor() as c:c.execute('SELECT pg_advisory_xact_lock'+('' if exclusive else '_shared')+'(%s)',[LOCK])
        yield

def enabled():return bool(OperationalState.objects.filter(key='maintenance').values_list('value',flat=True).first() or {})

class MaintenanceMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.method not in ('GET','HEAD','OPTIONS'):
            with gate():
                if enabled():
                    response=HttpResponse('Kurze Wartung/Sicherung. Änderungen bleiben bei Ihnen; bitte danach erneut versuchen.',status=503,content_type='text/plain; charset=utf-8');response['Retry-After']='60';return response
                return self.get_response(request)
        return self.get_response(request)
