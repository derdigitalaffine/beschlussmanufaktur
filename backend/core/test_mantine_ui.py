"""Mantine is strictly progressive enhancement of server-rendered, authorized HTML.

These tests protect the fallback and method/CSRF contracts even when client JS is
not available; browser tests cover mounting and focus/resize separately.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from .forms import MembershipChangeForm, MembershipRevokeForm


class MantineTemplateContracts(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            pk="org1",
            role="clerk",
            organization=SimpleNamespace(name="Stadt Test", get_kind_display=lambda: "Stadt"),
            get_role_display=lambda: "Sitzungsdienst",
        )

    def request(self):
        req = self.factory.get("/")
        req.resolver_match = resolve("/")
        req.user = SimpleNamespace(
            is_authenticated=True, username="test@example.invalid", first_name="Elena",
        )
        return req

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context")
    def test_dashboard_keeps_server_fallback_and_opt_in_island(self, active, manage):
        active.return_value = self.context
        html = render_to_string(
            "dashboard.html",
            {"context": self.context, "contexts": [self.context], "internal": True,
             "can_manage": False, "today_open_count": 0},
            request=self.request(),
        )
        self.assertIn('id="mantine-dashboard"', html)
        self.assertIn('class="card next-step"', html)
        self.assertIn("Sitzung planen", html)
        self.assertIn('mantine/workspace.js', html)
        self.assertIn('mantine/workspace.css', html)
        self.assertIn('data-fa-icon="home"', html)
        self.assertIn('ux-polish.css', html)
        self.assertIn('class="bm-private-ui"', html)
        self.assertIn('aria-label="Hauptnavigation"', html)
        self.assertIn('method="post"', html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_membership_edit_keeps_csrf_version_and_reason(self, active, manage):
        active.return_value = self.context
        form = MembershipChangeForm(
            initial={"role": "clerk", "version": 3, "reason": "Test"},
        )
        html = render_to_string(
            "membership_form.html",
            {"context": self.context, "title": "Rolle bearbeiten", "button": "Änderung speichern",
             "membership": SimpleNamespace(user=SimpleNamespace(email="person@example.invalid"),
                                           get_role_display=lambda: "Sitzungsdienst"),
             "form": form},
            request=self.request(),
        )
        self.assertIn('id="membership-fallback"', html)
        self.assertIn('id="mantine-membership"', html)
        self.assertIn('name="version"', html)
        self.assertIn('name="reason"', html)
        self.assertIn('name="role"', html)
        self.assertIn("person@example.invalid", html)
        self.assertIn('method="post"', html)
        self.assertIn("csrfmiddlewaretoken", html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_membership_revoke_remains_server_post_with_audit_reason(self, active, manage):
        active.return_value = self.context
        form = MembershipRevokeForm(initial={"version": 12})
        html = render_to_string(
            "membership_form.html",
            {"context": self.context, "title": "Zugriff entziehen", "button": "Zugriff entziehen",
             "membership": SimpleNamespace(user=SimpleNamespace(email="person@example.invalid"),
                                           get_role_display=lambda: "Sitzungsdienst"),
             "form": form},
            request=self.request(),
        )
        self.assertIn('id="membership-fallback"', html)
        self.assertIn('name="version"', html)
        self.assertIn('name="reason"', html)
        self.assertIn("Zugriff entziehen", html)

    @override_settings(SERVER_ROLE="public")
    @patch("core.portal_configuration.for_request", return_value=None)
    def test_public_visitor_never_loads_authenticated_ui_assets(self, portal):
        req = self.factory.get("/")
        req.resolver_match = resolve("/")
        req.user = AnonymousUser()
        html = render_to_string("base.html", {}, request=req)
        self.assertNotIn("mantine/shell.js", html)
        self.assertNotIn("ux-polish.css", html)
        self.assertNotIn('class="bm-private-ui"', html)
