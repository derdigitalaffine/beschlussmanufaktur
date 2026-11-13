"""Onboarding and public UI contracts: all URLs, CSRF and publication checks are server-owned."""
from pathlib import Path
from types import SimpleNamespace

from django import forms
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve


TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
STATIC = Path(__file__).resolve().parents[1] / "static"


def source(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


class OnboardingPublicUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.form = type("AccessForm", (forms.Form,), {
            "email": forms.EmailField(label="E-Mail-Adresse", required=True),
            "password": forms.CharField(
                label="Passwort", required=True, widget=forms.PasswordInput,
            ),
        })()

    def request(self):
        req = self.factory.get("/")
        req.resolver_match = resolve("/")
        req.user = AnonymousUser()
        return req

    def test_guest_pages_use_no_private_workbench_and_keep_csrf(self):
        pages = ["auth.html", "invitation_code.html", "invitation_accept.html", "recovery.html"]
        for page in pages:
            with self.subTest(page=page):
                content = source(page)
                self.assertIn("ux-onboarding.css", content)
                self.assertIn("{% csrf_token %}", content)
                self.assertIn('method="post"', content)
                self.assertNotIn("mantine/workbench.js", content)
                self.assertNotIn("novalidate", content)

    def test_sign_in_two_step_and_browser_passkey_hook(self):
        html = render_to_string("auth.html", {
            "title": "Anmelden", "description": "Anmeldung",
            "code_step": False, "button": "Anmelden", "form": self.form,
        }, request=self.request())
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="password"', html)
        self.assertIn('data-passkey="login"', html)
        self.assertIn('id="passkey-status"', html)
        self.assertIn("passkeys.js", html)
        self.assertIn('class="bm-guest-ui"', html)
        self.assertNotIn("mantine/workbench.js", html)
        code = render_to_string("auth.html", {
            "title": "E-Mail-Code", "description": "Bestätigen",
            "code_step": True, "button": "Bestätigen", "form": self.form,
        }, request=self.request())
        self.assertIn("Schritt 2 von 2", code)
        self.assertIn("Neuen Code anfordern", code)
        self.assertNotIn('data-passkey="login"', code)

    def test_invitation_code_retains_javascript_form_id_and_csrf(self):
        html = render_to_string("invitation_code.html", {
            "form": self.form,
        }, request=self.request())
        self.assertIn('id="invitation-code-form"', html)
        self.assertIn('method="post"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn("invitation.js", html)
        self.assertIn("Es gibt keine freie Selbstregistrierung", html)

    def test_invite_accept_preserves_distinct_account_states(self):
        invite = SimpleNamespace(
            organization=SimpleNamespace(name="Musterkommune"),
            email="user@example.invalid",
            get_role_display=lambda: "Prüfung",
            starts_at=None, ends_at=None,
        )
        html = render_to_string("invitation_accept.html", {
            "invitation": invite, "wrong_account": True,
        }, request=self.request())
        self.assertIn("Anderes Konto angemeldet", html)
        self.assertNotIn("Einladung annehmen</button>", html)
        existing = render_to_string("invitation_accept.html", {
            "invitation": invite, "needs_login": True,
        }, request=self.request())
        self.assertIn("Bestehendes Konto verwenden", existing)
        self.assertNotIn("Einladung annehmen</button>", existing)
        accept = render_to_string("invitation_accept.html", {
            "invitation": invite, "form": self.form,
        }, request=self.request())
        self.assertIn('name="csrfmiddlewaretoken"', accept)
        self.assertIn("Einladung annehmen</button>", accept)
        self.assertIn("Musterkommune", accept)

    def test_recovery_says_data_not_immediately_active(self):
        for situation in ["submitted", "done"]:
            with self.subTest(situation=situation):
                html = render_to_string("recovery.html", {
                    situation: True,
                }, request=self.request())
                self.assertNotIn('name="csrfmiddlewaretoken"', html)
                self.assertNotIn("Geprüft übernehmen</button>", html)
        done = render_to_string("recovery.html", {
            "done": True,
        }, request=self.request())
        self.assertIn("Die neuen Daten gelten erst danach.", done)

    def test_public_search_and_detail_remain_server_authoritative(self):
        public = source("public.html")
        detail = source("public_detail.html")
        self.assertTrue((STATIC / "ux-onboarding.css").is_file())
        for contract in [
            'method="get"', 'name="q"', 'name="organisation"',
            'name="gremium"', 'name="art"', 'name="von"', 'name="bis"',
            "{% for record in page %}", "{% url 'public_detail' record.pk %}",
            "{% if page.has_previous %}", "{% if page.has_next %}",
        ]:
            with self.subTest(search=contract):
                self.assertIn(contract, public)
        for contract in [
            "{{ body|safe }}", "{% if record.kind == 'template' %}",
            "{% url 'replica_export' record.pk 'pdf' %}",
            "{% url 'replica_asset' record.pk a.id %}",
            "{% if record.attachments %}",
        ]:
            with self.subTest(detail=contract):
                self.assertIn(contract, detail)
        for content in [public, detail]:
            self.assertNotIn("mantine/workbench.js", content)
            self.assertNotIn("{% csrf_token %}", content)
