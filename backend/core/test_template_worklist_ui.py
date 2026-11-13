from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from .template_views import index


def template_row(subject, state):
    return SimpleNamespace(
        pk=uuid4(), subject=subject, state=state,
        kind=SimpleNamespace(name="Beschlussvorlage"), number="",
        version=2, updated_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
        unit=None, get_classification_display=lambda: "Verwaltungsintern",
    )


@override_settings(SERVER_ROLE="internal")
class TemplateWorklistUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            role="reviewer",
            organization=SimpleNamespace(name="Musterstadt"),
            get_role_display=lambda: "Prüfende Person",
        )

    def render_page(self, query, rows, allowed=None):
        request = self.factory.get("/vorlagen/", query)
        request.user = SimpleNamespace(is_authenticated=True, first_name="Pat", username="tester")
        request.resolver_match = resolve("/vorlagen/")
        request.session = {}
        request._messages = []
        with (
            patch("core.template_views.active_context", return_value=self.context),
            patch("core.shell.active_context", return_value=self.context),
            patch("core.template_views.template_access", side_effect=lambda ctx, action, row: allowed is None or row in allowed),
            patch("core.template_views.Template.objects.select_related") as queryset,
            patch("core.template_views.Notification.objects.filter") as notifications,
        ):
            queryset.return_value.filter.return_value.__getitem__.return_value = rows
            notifications.return_value.order_by.return_value.__getitem__.return_value = []
            return index(request)

    def test_filter_only_renders_readable_review_documents(self):
        review = template_row("Prüfungsbedürftiger Vorgang", "review")
        draft = template_row("Interner Entwurf", "draft")
        hidden = template_row("Vertraulich versteckt", "review")
        response = self.render_page({"q": "Vorgang", "state": "review"}, [review, draft, hidden], [review, draft])
        html = response.content.decode("utf-8")
        self.assertContains(response, "Prüfungsbedürftiger Vorgang")
        self.assertContains(response, "In Prüfung")
        self.assertNotIn("Interner Entwurf", html)
        self.assertNotIn("Vertraulich versteckt", html)
        self.assertIn('value="review" selected', html)
        self.assertIn("1 Vorlagen angezeigt", html)

    def test_unknown_state_uses_valid_default_without_hidden_matches(self):
        draft = template_row("Ein erlaubter Entwurf", "draft")
        response = self.render_page({"state": "not-a-state"}, [draft])
        self.assertContains(response, "Ein erlaubter Entwurf")
        self.assertContains(response, "Entwurf")
        self.assertNotContains(response, "Statusfilter aktiv")

    def test_missing_context_is_denied(self):
        request = self.factory.get("/vorlagen/")
        request.user = SimpleNamespace(is_authenticated=True)
        with patch("core.template_views.active_context", return_value=None):
            with self.assertRaises(PermissionDenied):
                index(request)

    def test_reviewer_shortcut_keeps_encoded_search_context(self):
        row = template_row("Brücke & Rathaus", "review")
        response = self.render_page({"q": "Brücke & Rathaus"}, [row])
        self.assertContains(response, 'href="/vorlagen/?state=review&amp;q=Br%C3%BCcke+%26+Rathaus"')
        self.assertContains(response, "Vorlagen in Prüfung")
