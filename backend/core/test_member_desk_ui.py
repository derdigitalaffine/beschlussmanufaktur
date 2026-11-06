from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .member_views import desk


def meeting_row():
    pk=uuid4()
    return {
        "id":pk,"kind":"meeting","title":"Ratssitzung im Dezember",
        "subtitle":"Musterstadt · Gemeinderat",
        "url":f"/sitzungen/{pk}/","starts_at":timezone.now()+timedelta(days=7),
        "location":"Ratssaal","version":3,"status_label":"Eingeladen",
    }


@override_settings(SERVER_ROLE="internal")
class MemberDeskUITests(SimpleTestCase):
    def setUp(self):
        self.factory=RequestFactory()
        self.context=SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="member", user_id=uuid4(), get_role_display=lambda:"Ratsmitglied",
        )

    def request(self,method="get",data=None):
        request=(self.factory.post("/mein-bereich/",data) if method=="post"
                 else self.factory.get("/mein-bereich/",data))
        request.user=SimpleNamespace(is_authenticated=True, pk=self.context.user_id,username="test")
        request.resolver_match=resolve("/mein-bereich/")
        request.session={}
        request._messages=[]
        return request

    def test_next_meeting_and_offline_limits_are_visible(self):
        item=meeting_row()
        with (
            patch("core.member_views.active_context",return_value=self.context),
            patch("core.shell.active_context",return_value=self.context),
            patch("core.member_views.resources",return_value=[item]),
            patch("core.member_views.WorkspaceEntry.objects.filter",return_value=[]),
            patch("core.member_views.Notification.objects.filter") as notifications,
        ):
            notifications.return_value.order_by.return_value.__getitem__.return_value=[]
            response=desk(self.request())
        self.assertContains(response,"Ratssitzung im Dezember")
        self.assertContains(response,"Eingeladen")
        self.assertContains(response,"Persönliche Notiz")
        self.assertContains(response,"nicht automatisch offline verfügbar")
        self.assertContains(response,"Abstimmungen bleiben ausschließlich online")
        self.assertContains(response,'name="resource_id"')

    def test_forged_favorite_not_in_allowed_resources_is_rejected(self):
        allowed=meeting_row()
        unknown_id=uuid4()
        with (
            patch("core.member_views.active_context",return_value=self.context),
            patch("core.member_views.resources",return_value=[allowed]),
        ):
            with self.assertRaises(PermissionDenied):
                desk(self.request("post",{"kind":"meeting","resource_id":str(unknown_id)}))

    def test_empty_results_do_not_claim_offline_sync(self):
        with (
            patch("core.member_views.active_context",return_value=self.context),
            patch("core.shell.active_context",return_value=self.context),
            patch("core.member_views.resources",return_value=[]),
            patch("core.member_views.WorkspaceEntry.objects.filter",return_value=[]),
            patch("core.member_views.Notification.objects.filter") as notifications,
        ):
            notifications.return_value.order_by.return_value.__getitem__.return_value=[]
            response=desk(self.request())
        self.assertContains(response,"Keine freigegebenen Treffer")
        self.assertContains(response,"Keine zukünftige Sitzung")
