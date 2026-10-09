from django.conf import settings
from django.urls import path
from core import react_workspace, tls_management, recovery, emergency, passkeys, factors, identities, sample_data, imports, mail_views, person_profiles, portal_configuration, public_portal, offline_views, member_views, decision_views, minutes_views, session_views, session_transfer, vote_views, live_views, invitation_views, meeting_views, replica_views, collaboration_views, template_views, exchange, exchange_views, access_views, registry, user_views, views

urlpatterns = [
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
if settings.SERVER_ROLE in ('protected','public'):
    urlpatterns += [path('transfer/inbox/', exchange.inbox),path('transfer/assets/',exchange.receive_asset),path('dokumente/<uuid:document_id>/anlagen/<uuid:asset_id>/',replica_views.asset,name='replica_asset'),path('dokumente/<uuid:document_id>/export/<str:format>/',replica_views.document_export,name='replica_export')]
if settings.SERVER_ROLE == 'protected':
    urlpatterns += [path('transfer/sessions/',session_transfer.returns_endpoint),path('transfer/events/',exchange.events),path('transfer/ack/',exchange.acknowledge),path('vorlagen/',replica_views.documents,name='replica_documents'),path('dokumente/<uuid:document_id>/',replica_views.document,name='replica_document'),path('dokumente/<uuid:document_id>/vorschlag/',replica_views.propose_document,name='replica_propose'),path('unterlagen/',exchange_views.external_records,name='external_records'),path('unterlagen/<uuid:record_id>/vorschlag/',exchange_views.propose,name='propose')]
if settings.SERVER_ROLE=='protected':
    urlpatterns += [path('sitzungen/',meeting_views.index,name='meetings'),path('sitzungen/<uuid:meeting_id>/',meeting_views.detail,name='meeting_detail'),path('einladungen/<uuid:invitation_id>/<str:format>/',invitation_views.download,name='meeting_invitation_download'),path('einladungen/status/<int:delivery_id>/',invitation_views.seen,name='meeting_invitation_seen')]
if settings.SERVER_ROLE in ('internal','protected'):
    urlpatterns += [
        path('arbeitsplatz/', react_workspace.shell, name='react_workspace'),
        path('api/v1/arbeitsplatz/', react_workspace.bootstrap, name='workspace_bootstrap'),
        path('api/v1/arbeitsplatz/ressourcen/', react_workspace.resource_list, name='workspace_resources'),
        path('api/v1/arbeitsplatz/kontext/', react_workspace.select_context, name='workspace_context'),
        path('api/v1/arbeitsplatz/favorit/', react_workspace.favorite, name='workspace_favorite'),
        path('api/v1/arbeitsplatz/modus/', react_workspace.mode, name='workspace_mode'),
    ]
if settings.SERVER_ROLE in ('internal','protected'):
    urlpatterns += [path('offline/sitzungen/',offline_views.meetings,name='offline_meetings'),path('offline/identitaet/',offline_views.identity,name='offline_identity'),path('offline/abgleich/',offline_views.sync,name='offline_sync'),path('offline/sitzungen/<uuid:meeting_id>/',offline_views.prepare,name='offline_prepare'),path('offline/notizen/<uuid:meeting_id>/',offline_views.sync_note,name='offline_note_sync'),path('mein-bereich/',member_views.desk,name='member_desk'),path('sitzungen/<uuid:meeting_id>/notiz/',member_views.note,name='personal_note'),path('sitzungen/<uuid:meeting_id>/niederschrift/',minutes_views.workspace,name='minutes'),path('sitzungen/<uuid:meeting_id>/niederschrift/<int:version>/<str:format>/',minutes_views.download,name='minutes_export'),path('sitzungen/<uuid:meeting_id>/rueckgabe/',session_views.returns,name='session_returns'),path('sitzungen/<uuid:meeting_id>/abstimmungen/',vote_views.workspace,name='votes'),path('sitzungen/<uuid:meeting_id>/live/',live_views.workspace,name='live_workspace'),path('sitzungen/<uuid:meeting_id>/live/status/',live_views.status,name='live_status'),path('sitzungen/<uuid:meeting_id>/live/heartbeat/',live_views.heartbeat,name='live_heartbeat')]
if settings.SERVER_ROLE == "public":
    urlpatterns += [path("personen/<uuid:record_id>/foto/",person_profiles.portrait,name="public_portrait"),path("portal.css",portal_configuration.stylesheet,name="portal_css"),path("", public_portal.index, name="home"),path("kalender.ics",public_portal.calendar_feed,name="public_calendar"),path("informationen/<uuid:record_id>/",public_portal.detail,name="public_detail"),path("api/v1/veroeffentlichungen/",public_portal.api,name="public_api")]
else:
    urlpatterns += [
        path("", views.dashboard, name="home"),
        path("anmelden/", views.sign_in, name="sign_in"),
        path("wiederherstellung/",recovery.reset,name="recovery_reset"),path("wiederherstellung/anfordern/",recovery.request_reset,name="recovery_request"),
        path("sicherheit/passkeys/",passkeys.workspace,name="passkeys"),path("sicherheit/passkeys/optionen/<str:purpose>/",passkeys.options,name="passkey_options"),path("sicherheit/passkeys/pruefen/",passkeys.verify,name="passkey_verify"),path("sicherheit/passkeys/<uuid:key_id>/entfernen/",passkeys.remove,name="passkey_remove"),
        path("anmelden/faktor/",factors.verify,name="factor_verify"),path("sicherheit/",factors.security,name="security"),
        path("anmelden/code/", views.verify_code, name="verify_code"),
        path("abmelden/", views.sign_out, name="sign_out"),
        path("kontext/", views.select_context, name="select_context"),
    ]
    if settings.SERVER_ROLE == "internal":
        urlpatterns += [
            path('betrieb/tls/',tls_management.workspace,name='tls_management'),
            path('verwaltung/wiederherstellung/',recovery.administrative,name='recovery_admin'),
            path('betrieb/notfall/',emergency.request_access,name='emergency_request'),path('verwaltung/notfall/',emergency.review,name='emergency_review'),
            path('verwaltung/identitaeten/',identities.workspace,name='person_identities'),
            path('verwaltung/beispieldaten/',sample_data.workspace,name='sample_data'),
            path('verwaltung/import/',imports.workspace,name='imports'),path('verwaltung/import/<uuid:batch_id>/',imports.workspace,name='import_detail'),
            path('verwaltung/posteingang/',mail_views.inbox,name='mail_inbox'),
            path('verwaltung/personen/',person_profiles.profiles,name='person_profiles'),path('verwaltung/personen/<uuid:profile_id>/',person_profiles.profiles,name='person_profile'),
            path('verwaltung/portal/',portal_configuration.configure,name='portal_configure'),
            path('beschluesse/',decision_views.index,name='decisions'),
            path('beschluesse/<uuid:decision_id>/',decision_views.detail,name='decision'),
            path('sitzungen/<uuid:meeting_id>/aktivieren/',live_views.activation,name='meeting_activate'),
            path('einladungen/<uuid:invitation_id>/<str:format>/',invitation_views.download,name='meeting_invitation_download'),
            path('einladungen/status/<int:delivery_id>/',invitation_views.seen,name='meeting_invitation_seen'),
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
            path('struktur/beziehungen/<int:relation_id>/',registry.relation,name='relation_edit'),
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
