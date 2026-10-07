from django.conf import settings
from django.urls import path
from core import template_views, exchange, exchange_views, access_views, registry, user_views, views

urlpatterns = [
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
if settings.SERVER_ROLE in ('protected','public'):
    urlpatterns += [path('transfer/inbox/', exchange.inbox)]
if settings.SERVER_ROLE == 'protected':
    urlpatterns += [path('transfer/events/',exchange.events),path('transfer/ack/',exchange.acknowledge),path('unterlagen/',exchange_views.external_records,name='external_records'),path('unterlagen/<uuid:record_id>/vorschlag/',exchange_views.propose,name='propose')]
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
            path('vorlagen/',template_views.index,name='templates'),
            path('vorlagen/neu/',template_views.edit,name='template_new'),
            path('vorlagen/vorschau/',template_views.preview,name='template_preview'),
            path('vorlagen/<uuid:template_id>/',template_views.detail,name='template_detail'),
            path('vorlagen/<uuid:template_id>/bearbeiten/',template_views.edit,name='template_edit'),
            path('vorlagen/<uuid:template_id>/beteiligt/',template_views.heartbeat,name='template_heartbeat'),
            path('vorlagen/<uuid:template_id>/version/<int:version>/',template_views.compare,name='template_compare'),
            path('vorlagen/<uuid:template_id>/anlagen/',template_views.upload,name='attachment_upload'),
            path('anlagen/<uuid:attachment_id>/',template_views.download,name='attachment_download'),
            path('anlagen/<uuid:attachment_id>/status/',template_views.attachment_change,name='attachment_change'),
            path('austausch/',exchange_views.index,name='exchange'),
            path('austausch/<uuid:change_id>/',exchange_views.review,name='review_remote'),
            path('rechte/', access_views.grants, name='grants'),
            path('rechte/<uuid:grant_id>/entziehen/', access_views.revoke, name='revoke_grant'),
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
