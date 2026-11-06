from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .meeting_views import index


def row(title, state, starts_at):
    return SimpleNamespace(
        pk=uuid4(), title=title, state=state, starts_at=starts_at,
        committee=SimpleNamespace(name="Hauptausschuss"), location="Rathaus", version=3,
    )


@override_settings(SERVER_ROLE="internal")
class MeetingWorklistUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="clerk", get_role_display=lambda: "Sitzungsdienst",
        )

    def render_page(self, params, meetings, allowed=None):
        request = self.factory.get("/sitzungen/", params)
        request.user = SimpleNamespace(is_authenticated=True, username="clerk", first_name="Alex")
        request.resolver_match = resolve("/sitzungen/")
        request.session = {}
        request._messages = []
        with (
            patch("core.meeting_views.active_context", return_value=self.context),
            patch("core.shell.active_context", return_value=self.context),
            patch("core.meeting_views.meeting_access", side_effect=lambda ctx, action, item: allowed is None or item in allowed),
            patch("core.meeting_views.Meeting.objects.filter") as queryset,
        ):
            queryset.return_value.select_related.return_value = meetings
            return index(request)

    def test_filter_only_uses_permitted_meetings(self):
        future = timezone.now() + timedelta(days=3)
        past = timezone.now() - timedelta(days=10)
        permitted = row("Sitzung Bauausschuss", "invited", future)
        wrong_state = row("Verwaltungsrunde", "preparation", past)
        denied = row("Vertrauliches Gremium", "invited", future)
        response = self.render_page({"q": "Sitzung", "state": "invited"}, [permitted, wrong_state, denied], [permitted, wrong_state])
        html = response.content.decode("utf-8")
        self.assertContains(response, "Sitzung Bauausschuss")
        self.assertContains(response, "Eingeladen")
        self.assertNotIn("Vertrauliches Gremium", html)
        self.assertNotIn("Verwaltungsrunde", html)
        self.assertIn('value="invited" selected', html)
        self.assertIn("2</strong><span>Zugängliche Sitzungen", html)

    def test_unknown_state_does_not_hide_authorized_results(self):
        meeting = row("Sitzung Ortsbeirat", "finished", timezone.now() - timedelta(days=30))
        response = self.render_page({"state": "unknown"}, [meeting])
        self.assertContains(response, "Sitzung Ortsbeirat")
        self.assertNotContains(response, "Filter aktiv")

    def test_without_context_denied(self):
        request = self.factory.get("/sitzungen/")
        request.user = SimpleNamespace(is_authenticated=True)
        with patch("core.meeting_views.active_context", return_value=None):
            with self.assertRaises(PermissionDenied):
                index(request)

    @override_settings(SERVER_ROLE="protected")
    def test_protected_server_does_not_offer_planning(self):
        meeting = row("Sitzung Rat", "invited", timezone.now() + timedelta(days=1))
        response = self.render_page({}, [meeting])
        self.assertNotContains(response, "Neue Sitzung planen")
