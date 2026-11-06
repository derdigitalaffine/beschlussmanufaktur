from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


@override_settings(SERVER_ROLE="internal")
class MinutesUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.scribe_id = uuid4()
        self.meeting = SimpleNamespace(
            pk=uuid4(), title="Ratssitzung", version=8, state="finished",
            scribe_id=self.scribe_id, chair_id=uuid4(),
        )
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="clerk", get_role_display=lambda: "Sitzungsdienst",
        )

    def render_minutes(self, minutes=None, **changes):
        request = self.factory.get("/sitzungen/" + str(self.meeting.pk) + "/niederschrift/")
        request.resolver_match = resolve(request.path)
        request.user = SimpleNamespace(
            is_authenticated=True, username="scribe", pk=self.scribe_id,
            advanced_mode=False,
        )
        request.session = {}
        request._messages = []
        variables = {
            "context": self.context, "obj": self.meeting,
            "minutes": minutes, "editable": True, "can_publish": True,
            "can_export": True, "chosen": None, "error": None,
            "shown": {"kind": "result", "markdown": "Öffentliche Beschlüsse im Sitzungsjournal",
                      "public_markdown": "Freigabefassung"},
            "preview": "Öffentliche Beschlüsse im Sitzungsjournal",
            "versions": [], "corrections": [],
        }
        variables.update(changes)
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("minutes.html", variables, request=request)

    def test_approved_minutes_separate_publication_and_correction(self):
        minutes = SimpleNamespace(version=4, state="approved", published_version=None,
                                  ui_status="Durch Vorsitz geprüft", ui_tone="success")
        html = self.render_minutes(minutes)
        for text in ("Niederschrift", "Fassung 4", "Nicht veröffentlicht",
                     "Geprüfte öffentliche Fassung veröffentlichen",
                     "Begründete Berichtigungsfassung eröffnen",
                     "Fassungen und Prüfungen"):
            self.assertIn(text, html)
        self.assertNotIn('value="withdraw"', html)
        self.assertIn('name="version"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)

    def test_non_publisher_sees_no_publication_action(self):
        minutes = SimpleNamespace(version=3, state="approved", published_version=3,
                                  ui_status="Durch Vorsitz geprüft", ui_tone="success")
        html = self.render_minutes(minutes, editable=False, can_publish=False,
                                   can_export=False)
        self.assertIn("Öffentliche Fassung 3 bereitgestellt", html)
        self.assertNotIn('value="publish"', html)
        self.assertNotIn('value="withdraw"', html)
        self.assertNotIn('name="version"', html)

    def test_only_finished_meeting_can_offer_create_action(self):
        html = self.render_minutes(None)
        self.assertIn("Noch keine Niederschrift angelegt", html)
        self.assertIn('value="create"', html)
        self.meeting.state = "live"
        html = self.render_minutes(None)
        self.assertNotIn('value="create"', html)

    def test_archived_version_remains_read_only(self):
        minutes = SimpleNamespace(version=4, state="draft", published_version=None,
                                  ui_status="Entwurf", ui_tone="attention")
        chosen = SimpleNamespace(version=2)
        html = self.render_minutes(minutes, chosen=chosen, editable=True)
        self.assertIn("Archivfassung 2", html)
        self.assertNotIn('name="version"', html)
        self.assertNotIn('value="publish"', html)
