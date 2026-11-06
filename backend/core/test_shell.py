from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from .shell import workspace_shell


def demo_context(role="clerk"):
    organization = SimpleNamespace(
        name="Beispielgemeinde",
        get_kind_display=lambda: "Gemeinde",
    )
    return SimpleNamespace(
        pk="context-1",
        organization=organization,
        role=role,
        get_role_display=lambda: "Sitzungsdienst",
    )


class WorkspaceShellTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, authenticated=True):
        request = self.factory.get("/")
        request.resolver_match = resolve("/")
        request.user = (
            SimpleNamespace(is_authenticated=True, username="test", first_name="Test")
            if authenticated else AnonymousUser()
        )
        return request

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.active_context")
    def test_anonymous_user_has_no_shell_context(self, active):
        result = workspace_shell(self.request(authenticated=False))
        self.assertIsNone(result["shell_context"])
        self.assertFalse(result["shell_can_manage"])
        active.assert_not_called()

    @override_settings(SERVER_ROLE="public")
    @patch("core.shell.active_context")
    def test_public_server_never_exposes_work_context(self, active):
        result = workspace_shell(self.request())
        self.assertIsNone(result["shell_context"])
        self.assertFalse(result["shell_internal"])
        active.assert_not_called()

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context")
    def test_dashboard_shows_context_and_role_specific_action(self, active, manage):
        context = demo_context()
        active.return_value = context
        html = render_to_string(
            "dashboard.html",
            {"context": context, "contexts": [context], "can_manage": False, "internal": True},
            request=self.request(),
        )
        self.assertIn("Aktiver Arbeitskontext", html)
        self.assertIn("Beispielgemeinde", html)
        self.assertIn("Sitzung planen", html)
        self.assertIn("Der Weg zum Beschluss", html)
        self.assertIn('aria-label="Hauptnavigation"', html)
        self.assertIn('action="/mein-bereich/"', html)
        self.assertNotIn("Weitere Verwaltungsfunktionen", html)
        manage.assert_called()

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context", return_value=None)
    def test_no_context_disables_workflow_navigation(self, active, manage):
        html = render_to_string(
            "dashboard.html",
            {"context": None, "contexts": [], "can_manage": False, "internal": True},
            request=self.request(),
        )
        self.assertIn("Kein Arbeitskontext ausgewählt", html)
        self.assertNotIn('aria-label="Hauptnavigation"', html)
        self.assertNotIn("Sitzung planen", html)
        manage.assert_called()
