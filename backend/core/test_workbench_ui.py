"""The global workbench adds navigation, never domain authority or JS-only flows."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


class WorkbenchBaseTemplateTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            pk="org-test", role="clerk",
            organization=SimpleNamespace(name="Musterkommune"),
            get_role_display=lambda: "Sitzungsdienst",
        )

    def request(self, authenticated=True):
        request = self.factory.get("/")
        request.resolver_match = resolve("/")
        request.user = (SimpleNamespace(
            is_authenticated=True, first_name="Test", username="test@example.invalid",
        ) if authenticated else AnonymousUser())
        return request

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context")
    def test_private_navigation_and_mantine_assets_are_server_scoped(self, active, manage):
        active.return_value = self.context
        html = render_to_string("base.html", {}, request=self.request())
        self.assertIn('id="bm-workbench-root"', html)
        self.assertIn('class="bm-private-ui"', html)
        self.assertIn('data-bm-route="home"', html)
        self.assertIn("mantine/workbench.js", html)
        self.assertIn("mantine/workspace.css", html)
        self.assertIn("ux-workbench.css", html)
        self.assertIn('aria-label="Hauptnavigation"', html)
        self.assertIn("Musterkommune", html)
        # UI availability must remain bounded by may_manage_organization.
        self.assertNotIn('href="/benutzer/"', html)
        self.assertNotIn("ux-guest.css", html)
        manage.assert_called_once()

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context", return_value=None)
    def test_no_context_does_not_enable_private_navigation(self, active, manage):
        html = render_to_string("base.html", {}, request=self.request())
        self.assertIn('id="bm-workbench-root"', html)
        self.assertNotIn('aria-label="Hauptnavigation"', html)

    @override_settings(SERVER_ROLE="public")
    @patch("core.portal_configuration.for_request", return_value=None)
    def test_public_view_never_loads_private_workbench(self, portal):
        html = render_to_string("public.html", {
            "portal": SimpleNamespace(title="Öffentliche Informationen", introduction="Willkommen"),
            "filters": SimpleNamespace(q="", organisation="", gremium="", art="", von="", bis=""),
            "organizations": [], "committees": [], "page": [],
        }, request=self.request(authenticated=False))
        self.assertIn('class="bm-public-ui"', html)
        self.assertIn("ux-guest.css", html)
        self.assertNotIn("workbench.js", html)
        self.assertNotIn("mantine/workspace.css", html)
        self.assertNotIn("ux-workbench.css", html)
        self.assertNotIn('id="bm-workbench-root"', html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.active_context")
    def test_login_works_without_client_workbench(self, active):
        html = render_to_string("base.html", {}, request=self.request(authenticated=False))
        self.assertIn('class="bm-guest-ui"', html)
        self.assertNotIn("mantine/workbench.js", html)
        self.assertNotIn('id="bm-workbench-root"', html)
        active.assert_not_called()

    def test_all_eligible_pages_extend_server_base_and_assets_exist(self):
        templates = Path(__file__).resolve().parents[1] / "templates"
        public = {"public.html", "public_detail.html"}
        for file in templates.glob("*.html"):
            if file.name in {"base.html", "live_fields.html"}:
                continue
            with self.subTest(template=file.name):
                data = file.read_text(encoding="utf-8")
                self.assertTrue(
                    "{% extends 'base.html' %}" in data or
                    '{% extends "base.html" %}' in data,
                    f"{file.name} should inherit shared design, guest/public and security shell",
                )
        static = Path(__file__).resolve().parents[1] / "static"
        self.assertTrue((static / "ux-workbench.css").is_file())
        self.assertTrue((static / "ux-guest.css").is_file())
