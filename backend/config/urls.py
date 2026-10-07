from django.conf import settings
from django.urls import path
from core import registry, user_views, views

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
        urlpatterns += [
            path('struktur/', registry.structure, name='structure'),
            path('stammdaten/', registry.index, name='registry'),
            path('stammdaten/<str:kind>/neu/', registry.edit, name='registry_new'),
            path('stammdaten/<str:kind>/<uuid:record_id>/', registry.edit, name='registry_edit'),
            path('ansicht/', registry.mode, name='mode'),
            path("organisationen/neu/", views.create_organization, name="create_organization"),
            path("benutzer/", user_views.users, name="users"),
            path("benutzer/rollen/<uuid:membership_id>/", user_views.edit_membership, name="edit_membership"),
            path("benutzer/rollen/<uuid:membership_id>/entziehen/", user_views.remove_membership, name="remove_membership"),
            path("benutzer/einladungen/<uuid:invitation_id>/zurueckziehen/", user_views.remove_invitation, name="remove_invitation"),
            path("einladung/", user_views.exchange_invitation, name="exchange_invitation"),
            path("einladung/annehmen/", user_views.finish_invitation, name="accept_invitation"),
        ]
