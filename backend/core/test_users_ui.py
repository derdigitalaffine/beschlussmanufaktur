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
class UsersWorkspaceUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="organization_admin",
            get_role_display=lambda: "Organisationsverwaltung",
        )

    def render_users(self, memberships=None, invitations=None, form=None, query=""):
        request = self.factory.get("/benutzer/", {"q": query})
        request.user = SimpleNamespace(
            is_authenticated=True, username="admin", first_name="Erika", advanced_mode=False,
        )
        request.resolver_match = resolve(request.path)
        request.session = {}
        request._messages = []
        context = {
            "context": self.context,
            "page": Paginator(memberships or [], 20).get_page(1),
            "invitations": invitations or [],
            "form": form or InvitationForm(),
            "query": query,
        }
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("users.html", context, request=request)

    def test_membership_status_and_explicit_revocation_paths(self):
        person = SimpleNamespace(
            first_name="Alex", last_name="Beispiel", email="alex@example.invalid",
        )
        member = SimpleNamespace(
            pk=uuid4(), user=person, get_role_display=lambda: "Sachbearbeitung",
            access_state="Aktiv", starts_at=timezone.now(),
            ends_at=None, revoked_at=None,
        )
        invitation = SimpleNamespace(
            pk=uuid4(), email="pat@example.invalid", get_role_display=lambda: "Prüfung",
            delivery_state="Offen", expires_at=timezone.now() + timedelta(days=3),
            accepted_at=None, revoked_at=None,
        )
        html = self.render_users([member], [invitation])
        for marker in (
            "Menschen &amp; Rollen", "Alex Beispiel", "Sachbearbeitung",
            "Aktiv", "Rolle bearbeiten", "Zugriff entziehen",
            "pat@example.invalid", "Einladung zurückziehen", "Person einladen",
            "Die Person erhält erst nach Annahme",
        ):
            self.assertIn(marker, html)
        self.assertIn(str(member.pk), html)
        self.assertIn(str(invitation.pk), html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="role"', html)

    def test_invalid_invitation_shows_errors_and_preserves_input(self):
        form = InvitationForm(data={
            "email": "unzulässig", "role": "author", "starts_at": "", "ends_at": "",
        })
        self.assertFalse(form.is_valid())
        html = self.render_users(form=form)
        self.assertIn("Einladung nicht versendet", html)
        self.assertIn('role="alert"', html)
        self.assertIn("unzulässig", html)
        self.assertIn("Nach Name oder E-Mail suchen", html)

    def test_empty_state_explains_access_after_acceptance(self):
        html = self.render_users()
        self.assertIn("Keine passenden Rollenzuordnungen", html)
        self.assertIn("Erste Person einladen", html)
        self.assertIn("Noch keine Einladungen versendet", html)
        self.assertIn("erst nach ihrer ausdrücklichen Annahme", html)
