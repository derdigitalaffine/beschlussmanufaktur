from django.conf import settings
from django.urls import path
from core import views

urlpatterns = [
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
if settings.SERVER_ROLE == "public":
    urlpatterns += [path("", views.public_home, name="home")]
else:
    urlpatterns += [
        path("", views.dashboard, name="home"),
        path("anmelden/", views.sign_in, name="sign_in"),
        path("anmelden/code/", views.verify_code, name="verify_code"),
        path("abmelden/", views.sign_out, name="sign_out"),
        path("kontext/", views.select_context, name="select_context"),
    ]
    if settings.SERVER_ROLE == "internal":
        urlpatterns += [path("organisationen/neu/", views.create_organization, name="create_organization")]

