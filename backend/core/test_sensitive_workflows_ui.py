"""High-stakes UI contracts: styling must never redefine safety or POST fields.

These checks intentionally complement server domain tests and role-specific
integration suites; they do not claim to prove realtime/offline correctness.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
STATIC = Path(__file__).resolve().parents[1] / "static"


def source(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


class SensitiveWorkflowsUIContracts(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            pk="00000000-0000-0000-0000-000000000001",
            organization=SimpleNamespace(name="Beispielgemeinde"),
            get_role_display=lambda: "Sitzungsdienst",
        )

    def request(self):
        req = self.factory.get("/")
        req.resolver_match = resolve("/")
        req.user = SimpleNamespace(
            is_authenticated=True, first_name="Test", username="test@example.invalid",
        )
        return req

    def test_all_workflows_have_local_css_with_no_new_client_logic(self):
        templates = [
            "security.html", "passkeys.html", "emergency.html",
            "session_returns.html", "personal_note.html",
            "replica_document.html", "template_compare.html",
            "live_workspace.html", "votes.html",
        ]
        self.assertTrue((STATIC / "ux-sensitive-workflows.css").is_file())
        for filename in templates:
            with self.subTest(filename=filename):
                content = source(filename)
                self.assertIn("ux-sensitive-workflows.css", content)
                self.assertIn("{% extends 'base.html' %}", content)
                self.assertNotIn("onclick=", content)
                self.assertNotIn("onchange=", content)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=False)
    @patch("core.shell.active_context")
    def test_factors_keep_server_post_actions_and_one_time_code_section(self, active, manage):
        active.return_value = self.context
        profile = SimpleNamespace(method="email", pending_secret=None)
        html = render_to_string("security.html", {
            "profile": profile, "form": None, "secret": "test-one-time-secret",
            "uri": "otpauth://totp/test", "codes": ["test-recovery-code"],
        }, request=self.request())
        self.assertIn('method="post"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('name="action" value="start_totp"', html)
        self.assertIn('name="action" value="email"', html)
        self.assertNotIn('name="action" value="recovery"', html)
        self.assertIn("test-one-time-secret", html)
        self.assertIn("test-recovery-code", html)
        self.assertIn("Diese Codes werden nur hier einmal angezeigt", html)
        self.assertIn("ux-sensitive-workflows.css", html)

    def test_passkey_client_hooks_are_unchanged(self):
        html = source("passkeys.html")
        for contract in [
            'id="passkey-form"', 'name="password"', 'name="code"', 'name="name"',
            'data-passkey="reauth"', 'data-passkey="register"',
            'data-passkey-remove="{{ key.pk }}"',
            'id="passkey-status"', 'id="passkey-recovery"',
            'passkeys.js', "{% csrf_token %}",
        ]:
            with self.subTest(contract=contract):
                self.assertIn(contract, html)

    def test_emergency_and_return_version_contracts(self):
        emergency = source("emergency.html")
        for contract in [
            'name="request" value="{{ r.pk }}"',
            'name="decision" value="approve"',
            'name="decision" value="reject"',
            "{% if r.state == 'pending' and not technical %}",
        ]:
            self.assertIn(contract, emergency)
        returns = source("session_returns.html")
        for contract in [
            'name="expected_version" value="{{ obj.version }}"',
            'name="return_id" value="{{ change.pk }}"',
            'name="reason" required maxlength="1000"',
            "{% if not external and change.state == 'pending' %}",
        ]:
            self.assertIn(contract, returns)

    def test_private_note_and_protected_export_never_claim_client_saves(self):
        note = source("personal_note.html")
        for contract in [
            'method="post"', "{% csrf_token %}",
            'name="version" type="hidden" value="{{ version }}"',
            'name="markdown"', "{{ preview }}",
            "Ungespeicherte Änderungen erscheinen erst nach dem Speichern.",
        ]:
            self.assertIn(contract, note)
        protected = source("replica_document.html")
        for contract in [
            "{% if can_edit %}", "{% url 'replica_propose' obj.pk %}",
            "{% url 'replica_export' obj.pk 'pdf' %}",
            "{% url 'replica_export' obj.pk 'docx' %}",
            "{% url 'replica_asset' obj.pk a.id %}",
        ]:
            self.assertIn(contract, protected)

    def test_live_and_vote_payloads_keep_original_dom_protocol(self):
        live = source("live_workspace.html")
        vote = source("votes.html")
        for contract in [
            'id="live-connection"', 'id="live-heartbeat"',
            'name="expected_version"', 'name="item_id"',
            'name="kind" value="motion"', 'name="kind" value="quorum"',
            'name="kind" value="roster"', 'name="kind" value="conflict"',
            "live.js", "{% include 'live_fields.html' %}",
        ]:
            with self.subTest(live=contract):
                self.assertIn(contract, live)
        for contract in [
            'name="request_id" value="{{ request_id }}"',
            'name="action" value="cast"',
            'name="action" value="open"',
            'name="action" value="confirm"',
            'name="vote_id" value="{{ vote.pk }}"',
            'name="choice"',
            "{% include 'live_fields.html' %}",
        ]:
            with self.subTest(vote=contract):
                self.assertIn(contract, vote)
