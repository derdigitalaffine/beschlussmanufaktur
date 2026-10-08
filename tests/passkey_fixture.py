"""Isolated loopback-only fixture. Never copied into the application image."""
import os,sys,re,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings';os.environ['SERVER_ROLE']='internal'
import django
django.setup()
from django.conf import settings
settings.APPLICATION_URL='http://localhost:8766';settings.SESSION_COOKIE_SECURE=False;settings.CSRF_COOKIE_SECURE=False
from django.core.management import call_command
call_command('migrate',verbosity=0)
from core.models import User,Membership,Organization
user=User.objects.create_user('browser-person',email='browser@example.invalid',password='Browser-test-password-2026')
org=Organization.objects.create(name='Browserfixture',kind='association');Membership.objects.create(user=user,organization=org,role='organization_admin')
from django.urls import path
from config.urls import urlpatterns
from django.http import JsonResponse
from django.core import mail

def code(request):return JsonResponse({'code':re.search(r'\b\d{6}\b',mail.outbox[-1].body).group()})
module=types.ModuleType('passkey_fixture_urls');from django.views.static import serve
module.urlpatterns=urlpatterns+[path('fixture-code/',code),path('static/<path:path>',serve,{'document_root':str(Path(__file__).resolve().parents[1]/'backend/static')})];sys.modules[module.__name__]=module;settings.ROOT_URLCONF=module.__name__
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server
print('READY',flush=True);make_server('127.0.0.1',8766,get_wsgi_application()).serve_forever()
