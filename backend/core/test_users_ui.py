from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .forms import InvitationForm


@override_settings(SERVER_ROLE="internal")
class PeopleAndRolesUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="organization_admin", get_role_display=lambda: "Organisationsverwaltung",
        )

    def render_people(self, memberships=(), invitations=(), form=None, query=""):
        request = self.factory.get("/benutzer/")
        request.user = SimpleNamespace(is_authenticated=True, username="admin", first_name="Alex")
        request.resolver_match = resolve("/benutzer/")
        request.session = {}
        request._messages = []
        values = {
            "context": self.context,
            "form": form if form is not None else InvitationForm(),
            "page": Paginator(list(memberships), 20).get_page(1),
            "invitations": list(invitations),
            "query": query,
        }
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("users.html", values, request=request)

    def test_membership_state_and_actions_remain_explicit(self):
        now = timezone.now()
        person = SimpleNamespace(
            pk=uuid4(), access_state="Aktiv", role="author",
            get_role_display=lambda: "Sachbearbeitung",
            user=SimpleNamespace(first_name="Erika", last_name="Beispiel", email="erika@example.invalid"),
            starts_at=now - timedelta(days=12), ends_at=None, revoked_at=None,
        )
        expired = SimpleNamespace(
            pk=uuid4(), access_state="Entzogen", role="member",
            get_role_display=lambda: "Mandatsträger",
            user=SimpleNamespace(first_name="", last_name="", email="rat@example.invalid"),
            starts_at=now - timedelta(days=80), ends_at=None, revoked_at=now,
        )
        html = self.render_people([person, expired])
        self.assertIn("Menschen &amp; Rollen", html)
        self.assertIn("Erika Beispiel", html)
        self.assertIn("Aktiv", html)
        self.assertIn("Entzogen", html)
        self.assertIn(str(person.pk), html)
        self.assertNotIn(str(expired.pk), html)
        self.assertIn("Rolle bearbeiten", html)
        self.assertIn("Zugriff entziehen", html)
        self.assertIn('name="csrfmiddlewaretoken"', html)

    def test_invitation_status_and_revocation_are_separated(self):
        now = timezone.now()
        pending = SimpleNamespace(
            pk=uuid4(), email="neu@example.invalid", delivery_state="Offen",
            get_role_display=lambda: "Sachbearbeitung",
            expires_at=now + timedelta(days=5), accepted_at=None, revoked_at=None,
        )
        accepted = SimpleNamespace(
            pk=uuid4(), email="alt@example.invalid", delivery_state="Angenommen",
            get_role_display=lambda: "Mandatsträger",
            expires_at=now + timedelta(days=2), accepted_at=now, revoked_at=None,
        )
        html = self.render_people(invitations=[pending, accepted])
        self.assertIn("neu@example.invalid", html)
        self.assertIn("Angenommen", html)
        self.assertIn(str(pending.pk), html)
        self.assertNotIn(str(accepted.pk), html)
        self.assertIn("Einladung zurückziehen", html)

    def test_invitation_validation_renders_field_links_and_keeps_input(self):
        form = InvitationForm(data={"email": "ungueltig", "role": "author"})
        self.assertFalse(form.is_valid())
        html = self.render_people(form=form)
        self.assertIn("Einladung konnte nicht versendet werden", html)
        self.assertIn('role="alert"', html)
        self.assertIn('href="#id_email"', html)
        self.assertIn('value="ungueltig"', html)
        self.assertIn('name="role"', html)
        self.assertIn('name="starts_at"', html)
        self.assertIn('name="ends_at"', html)

    def test_empty_context_shows_safe_next_action(self):
        html = self.render_people(query="nichtvorhanden")
        self.assertIn("Keine passenden Rollen", html)
        self.assertIn("Suche löschen", html)
        self.assertIn("Noch keine Einladungen", html)
        self.assertIn("Person einladen", html)
