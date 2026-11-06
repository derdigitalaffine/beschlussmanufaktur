"""No-JS server-rendered contract for secondary administration workflows.

These pages reorganize field/help/error/status layout only. POST contracts,
CSRF tokens, form validation and server-side permissions must not change.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


class AdminWorkflowMarkupTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            pk=1, role="clerk",
            organization=SimpleNamespace(name="Musterkommune"),
            get_role_display=lambda: "Sitzungsdienst",
        )
        self.form = type("SampleForm", (forms.Form,), {
            "title": forms.CharField(label="Bezeichnung", required=True),
            "valid_until": forms.DateField(
                label="Gültigkeit", required=False,
                widget=forms.DateInput(attrs={"type": "date"}),
            ),
        })()

    def request(self):
        req = self.factory.get("/")
        req.resolver_match = resolve("/")
        req.user = SimpleNamespace(
            is_authenticated=True, first_name="Test", username="test@example.invalid",
        )
        return req

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_data_forms_keep_native_posts_labels_and_csrf(self, active, manage):
        active.return_value = self.context
        scenarios = [
            ("registry_form.html", {"title": "Mandat bearbeiten", "context": self.context}),
            ("admin_form.html", {"title": "Gremium bearbeiten", "description": "Angaben prüfen",
                                 "context": self.context, "button": "Speichern"}),
            ("organization_form.html", {"context": self.context}),
        ]
        for template, context in scenarios:
            with self.subTest(template=template):
                html = render_to_string(template, {
                    **context, "form": self.form,
                }, request=self.request())
                self.assertIn('class="bm-task-form"', html)
                self.assertIn('method="post"', html)
                self.assertIn('name="csrfmiddlewaretoken"', html)
                self.assertIn('name="title"', html)
                self.assertIn('name="valid_until"', html)
                self.assertIn('for="id_title"', html)
                self.assertIn("ux-admin-workflows.css", html)
                self.assertIn("mantine/workbench.js", html)
                self.assertNotIn("novalidate", html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_grants_separate_active_revoke_and_revoked_entry(self, active, manage):
        active.return_value = self.context
        membership = SimpleNamespace(
            user=SimpleNamespace(email="person@example.invalid"),
            get_role_display=lambda: "Sachbearbeitung",
        )
        grants = [
            SimpleNamespace(pk="00000000-0000-0000-0000-000000000001", membership=membership, resource_kind="template",
                            resource_id="t1", actions=["edit"], reason="Notwendig",
                            revoked_at=None),
            SimpleNamespace(pk="00000000-0000-0000-0000-000000000002", membership=membership, resource_kind="template",
                            resource_id="t2", actions=["view"], reason="Erledigt",
                            revoked_at="2026-11-06"),
        ]
        html = render_to_string("grants.html", {
            "context": self.context, "form": self.form, "grants": grants,
        }, request=self.request())
        self.assertIn("Einzelrecht zuweisen", html)
        self.assertIn('bm-access-revoked', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertEqual(html.count("Recht entziehen</button>"), 1)
        self.assertIn('name="title"', html)
        self.assertIn("person@example.invalid", html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_import_preview_is_not_equated_to_applied(self, active, manage):
        active.return_value = self.context
        batch = SimpleNamespace(
            kind="organization", rows=[{"name": "Gemeinde Test", "code": "123"}],
            applied_at=None,
        )
        html = render_to_string("imports.html", {
            "context": self.context, "batch": batch, "headers": {},
        }, request=self.request())
        self.assertIn("<details", html)
        self.assertIn("Datensatz 1", html)
        self.assertIn("Gemeinde Test", html)
        self.assertIn('name="confirm"', html)
        self.assertIn('value="yes"', html)
        self.assertIn("Geprüfte Daten übernehmen", html)
        self.assertNotIn("Übernommen am", html)

    @override_settings(SERVER_ROLE="internal")
    @patch("core.shell.may_manage_organization", return_value=True)
    @patch("core.shell.active_context")
    def test_tls_dns_check_and_apply_remain_distinct_server_post_actions(self, active, manage):
        active.return_value = self.context
        plan = SimpleNamespace(
            pk=5, hostname="ris.example.invalid", mode="letsencrypt",
            state="prepared", error="", proof="public-txt-marker",
            dns_verified_at=None, certificate_info=None,
        )
        html = render_to_string("tls_management.html", {
            "context": self.context, "form": self.form, "plans": [plan],
        }, request=self.request())
        self.assertIn('name="plan"', html)
        self.assertIn('name="operation" value="dns"', html)
        self.assertIn('name="operation" value="apply"', html)
        self.assertIn("noch nicht erfolgreich", html)
        self.assertIn("public-txt-marker", html)
        self.assertIn('enctype="multipart/form-data"', html)

    def test_protected_replica_search_preserves_get_filters_and_routes(self):
        # The normal test URLConf is intentionally bound to SERVER_ROLE=internal
        # at module import. Protected endpoints are separately covered by role
        # integration tests; avoid pretending they reverse under internal URLConf.
        from pathlib import Path

        template = (Path(__file__).resolve().parents[1] /
                    "templates" / "replica_documents.html").read_text(encoding="utf-8")
        self.assertIn('method="get"', template)
        self.assertIn('name="q"', template)
        self.assertIn('role="search"', template)
        self.assertIn("{% url 'replica_documents' %}", template)
        self.assertIn("{% url 'replica_document' obj.pk %}", template)
        self.assertIn('class="card bm-record"', template)
