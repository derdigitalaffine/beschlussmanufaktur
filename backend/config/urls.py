from django.conf import settings
from django.urls import path
from core import meeting_views, replica_views, collaboration_views, template_views, exchange, exchange_views, access_views, registry, user_views, views

urlpatterns = [
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
if settings.SERVER_ROLE in ('protected','public'):
    urlpatterns += [path('transfer/inbox/', exchange.inbox),path('transfer/assets/',exchange.receive_asset),path('dokumente/<uuid:document_id>/anlagen/<uuid:asset_id>/',replica_views.asset,name='replica_asset'),path('dokumente/<uuid:document_id>/export/<str:format>/',replica_views.document_export,name='replica_export')]
if settings.SERVER_ROLE == 'protected':
    urlpatterns += [path('transfer/events/',exchange.events),path('transfer/ack/',exchange.acknowledge),path('vorlagen/',replica_views.documents,name='replica_documents'),path('dokumente/<uuid:document_id>/',replica_views.document,name='replica_document'),path('dokumente/<uuid:document_id>/vorschlag/',replica_views.propose_document,name='replica_propose'),path('unterlagen/',exchange_views.external_records,name='external_records'),path('unterlagen/<uuid:record_id>/vorschlag/',exchange_views.propose,name='propose')]
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
            path('sitzungen/',meeting_views.index,name='meetings'),
            path('sitzungen/neu/',meeting_views.edit,name='meeting_new'),
            path('sitzungen/<uuid:meeting_id>/',meeting_views.detail,name='meeting_detail'),
            path('sitzungen/<uuid:meeting_id>/bearbeiten/',meeting_views.edit,name='meeting_edit'),
            path('sitzungen/<uuid:meeting_id>/top/neu/',meeting_views.agenda,name='meeting_agenda_new'),
            path('sitzungen/<uuid:meeting_id>/top/<uuid:item_id>/',meeting_views.agenda,name='meeting_agenda_edit'),
            path('sitzungen/<uuid:meeting_id>/einladen/',meeting_views.invite,name='meeting_invite'),
            path('sitzungen/<uuid:meeting_id>/nachtrag/',meeting_views.amendment,name='meeting_amendment'),
            path('sitzungen/<uuid:meeting_id>/gast/',meeting_views.guest,name='meeting_guest'),
            path('nachtraege/<uuid:change_id>/genehmigen/',meeting_views.approve,name='meeting_amendment_approve'),
            path('vorlagenarten/',collaboration_views.kind_list,name='kind_list'),
            path('vorlagenarten/neu/',collaboration_views.kind,name='kind_new'),
            path('vorlagenarten/<uuid:kind_id>/',collaboration_views.kind,name='kind_edit'),
            path('vorlagen/<uuid:template_id>/pruefer/',collaboration_views.add_step,name='template_add_step'),
            path('vorlagen/<uuid:template_id>/aktion/',collaboration_views.action,name='template_action'),
            path('vorlagen/<uuid:template_id>/beteiligung/',collaboration_views.participant,name='template_participant'),
            path('vorlagen/<uuid:template_id>/kommentar/',collaboration_views.comment,name='template_comment'),
            path('vorlagen/<uuid:template_id>/beratung/',collaboration_views.consultation,name='template_consultation'),
            path('vorlagen/<uuid:template_id>/verknuepfung/',collaboration_views.link,name='template_link'),
            path('vorlagen/<uuid:template_id>/export/<str:format>/',collaboration_views.document,name='template_export'),
            path('vorlagen/<uuid:template_id>/export/<str:format>/<int:version>/',collaboration_views.document,name='template_version_export'),
            path('pruefung/<int:step_id>/',collaboration_views.review,name='template_review'),
            path('beratung/<uuid:consultation_id>/',collaboration_views.amendment,name='consultation_amendment'),
            path('aufgaben/<int:comment_id>/erledigt/',collaboration_views.complete_task,name='template_task_complete'),
            path('hinweise/<int:notification_id>/gelesen/',collaboration_views.notification_read,name='notification_read'),
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
