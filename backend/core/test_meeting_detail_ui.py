from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .meeting_views import detail


def meeting():
    person = SimpleNamespace(get_full_name=lambda: "Erika Beispiel", email="erika@example.invalid")
    return SimpleNamespace(
        pk=uuid4(), state="preparation", title="Sitzung des Gemeinderats",
        organization=SimpleNamespace(name="Musterstadt"),
        committee=SimpleNamespace(name="Gemeinderat"), starts_at=timezone.now(),
        version=4, location="Ratssaal", chair=person, scribe=person,
        proposal_deadline=None, release_deadline=None, invitation_days=4,
        statutory_count=21, public_enabled=False,
        ui_status="In Vorbereitung", ui_tone="attention",
    )


@override_settings(SERVER_ROLE="internal")
class MeetingDetailUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="clerk", get_role_display=lambda: "Sitzungsdienst",
        )

    def test_detail_keeps_core_actions_and_status_legible(self):
        obj = meeting()
        item = SimpleNamespace(
            position=1, parent=None, public=True,
            title="Haushaltsplan 2027", id=uuid4(), template=None,
        )
        request = self.factory.get("/sitzungen/" + str(obj.pk) + "/")
        request.user = SimpleNamespace(is_authenticated=True, username="clerk")
        request.resolver_match = resolve(request.path)
        request.session = {}
        request._messages = []
        with patch("core.shell.active_context", return_value=self.context):
            html = render_to_string("meeting_detail.html", {
                "context":self.context,"obj":obj,
                "data":SimpleNamespace(items=[item]),
                "can_plan":True,"can_invite":True,"can_chair":True,
                "amendments":[],"deliveries":[],"memberships":[],
            }, request=request)
        for marker in (
            "Tagesordnung", "Haushaltsplan 2027", "In Vorbereitung",
            "Sitzungsführung", "Niederschrift", "Meine persönliche Notiz",
            "Kontrollierte Rückgabe", "TOP bearbeiten", "Einladung / neuen Versandstand",
            "Zusätzliche Teilnehmende",
        ):
            self.assertIn(marker, html)
        self.assertIn('aria-current="step"', html)
        self.assertIn('data-tone="attention"', html)

    @override_settings(SERVER_ROLE="protected")
    def test_protected_server_never_offers_internal_change_routes(self):
        obj = meeting()
        request = self.factory.get("/sitzungen/" + str(obj.pk) + "/")
        request.user = SimpleNamespace(is_authenticated=True, pk=uuid4())
        with (
            patch("core.meeting_views.active_context", return_value=self.context),
            patch("core.meeting_views.get_object_or_404", return_value=obj),
            patch("core.meeting_views.meeting_access", return_value=True),
            patch("core.meeting_views.meeting_snapshot", return_value=SimpleNamespace(items=[])),
            patch("core.meeting_views.InvitationDelivery.objects.filter") as deliveries,
            patch("core.meeting_views.MeetingAmendment.objects.filter", return_value=[]),
            patch("core.meeting_views.Membership.objects.filter") as members,
            patch("core.member_views.remember"),
            patch("core.meeting_views.render") as rendered,
        ):
            deliveries.return_value.select_related.return_value.order_by.return_value = []
            members.return_value.select_related.return_value = []
            detail(request, obj.pk)
            info = rendered.call_args.args[2]
            self.assertFalse(info["can_plan"])
            self.assertFalse(info["can_invite"])
            self.assertFalse(info["can_chair"])
