from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .decision_views import index


USER_ID = uuid4()


def decision_row(title, state, due_on=None, responsible_id=None):
    return SimpleNamespace(
        pk=uuid4(),
        wording=title + ": Beschlussfassung",
        status=state, due_on=due_on, responsible_id=responsible_id,
        responsible=None, version=2,
        vote=SimpleNamespace(
            meeting=SimpleNamespace(title="Gemeinderat am Freitag"),
            item=SimpleNamespace(title=title),
        ),
    )


@override_settings(SERVER_ROLE="internal")
class DecisionWorklistUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="clerk", get_role_display=lambda: "Sitzungsdienst",
        )

    def render_page(self, params, decisions, allowed=None):
        request = self.factory.get("/beschluesse/", params)
        request.user = SimpleNamespace(is_authenticated=True, username="clerk", pk=USER_ID)
        request.resolver_match = resolve("/beschluesse/")
        request.session = {}
        request._messages = []
        with (
            patch("core.decision_views.active_context", return_value=self.context),
            patch("core.shell.active_context", return_value=self.context),
            patch("core.decision_views.access", side_effect=lambda ctx, item: allowed is None or item in allowed),
            patch("core.decision_views.Decision.objects.select_related") as queryset,
        ):
            queryset.return_value.filter.return_value = decisions
            return index(request)

    def test_overdue_focus_excludes_nonpermitted_decisions_from_counts(self):
        past = timezone.localdate() - timedelta(days=4)
        visible = decision_row("Brücke sanieren", "in_progress", past, USER_ID)
        normal = decision_row("Parkpflege", "closed", past, USER_ID)
        denied = decision_row("Vertraulicher Beschluss", "open", past, USER_ID)
        response = self.render_page({"focus": "overdue"}, [visible, normal, denied], [visible, normal])
        html = response.content.decode("utf-8")
        self.assertContains(response, "Brücke sanieren")
        self.assertContains(response, "Frist überschritten")
        self.assertNotIn("Parkpflege", html)
        self.assertNotIn("Vertraulicher Beschluss", html)
        self.assertIn("1</strong><span>Überfällige Beschlüsse", html)
        self.assertIn("2</strong><span>Mir zugewiesen", html)

    def test_mine_filter_returns_only_assigned_decisions(self):
        mine = decision_row("Wegesanierung", "open", responsible_id=USER_ID)
        other = decision_row("Haushaltsplanung", "open", responsible_id=uuid4())
        response = self.render_page({"focus": "mine"}, [other, mine])
        self.assertContains(response, "Wegesanierung")
        self.assertNotContains(response, "Haushaltsplanung")
        self.assertContains(response, "Mir zugewiesen")

    def test_unknown_state_and_focus_default_to_all(self):
        available = decision_row("Kita-Instandsetzung", "reported")
        response = self.render_page({"state": "other", "focus": "other"}, [available])
        self.assertContains(response, "Kita-Instandsetzung")
        self.assertNotContains(response, "Filter aktiv")

    def test_no_context_denies_without_data_query(self):
        request = self.factory.get("/beschluesse/")
        request.user = SimpleNamespace(is_authenticated=True)
        with patch("core.decision_views.active_context", return_value=None):
            with self.assertRaises(PermissionDenied):
                index(request)

    def test_dashboard_shortcuts_preserve_search_and_state_with_encoded_urls(self):
        item=decision_row("Brücke & Tunnel", "in_progress",timezone.localdate()-timedelta(days=1),USER_ID)
        response=self.render_page({"q":"Brücke & Tunnel","state":"in_progress"},[item])
        self.assertContains(response,'href="/beschluesse/?focus=overdue&amp;q=Br%C3%BCcke+%26+Tunnel&amp;state=in_progress"')
        self.assertContains(response,'href="/beschluesse/?focus=mine&amp;q=Br%C3%BCcke+%26+Tunnel&amp;state=in_progress"')
        self.assertContains(response,"Brücke &amp; Tunnel")

    def test_shortcut_discards_invalid_state_and_focus(self):
        item=decision_row("Rathaus", "open")
        response=self.render_page({"state":"unexpected","focus":"bad"},[item])
        self.assertContains(response,'href="/beschluesse/?focus=overdue"')
        self.assertNotContains(response,"state=unexpected")

    def test_active_shortcut_has_accessible_current_state(self):
        item = decision_row("Wegesanierung", "open", responsible_id=USER_ID)
        response = self.render_page({"focus": "mine"}, [item])
        html = response.content.decode("utf-8")
        self.assertIn('href="/beschluesse/?focus=mine" aria-current="true"', html)
        self.assertNotIn('href="/beschluesse/?focus=overdue" aria-current="true"', html)
        self.assertIn('role="status" aria-live="polite"', html)
