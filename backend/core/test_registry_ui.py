from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


class RelationFixtureForm(forms.Form):
    target = forms.ChoiceField(label="Ziel", choices=[("other", "Andere Kommune")])
    reason = forms.CharField(label="Begründung")


@override_settings(SERVER_ROLE="internal")
class RegistryUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt", advanced_enabled=True),
            role="organization_admin",
            get_role_display=lambda: "Organisationsverwaltung",
        )

    def render_registry(self, records=None, mandates=None, relations=None):
        request = self.factory.get("/stammdaten/")
        request.user = SimpleNamespace(
            is_authenticated=True, username="admin", first_name="Alex", advanced_mode=True,
        )
        request.resolver_match = resolve(request.path)
        request.session = {}
        request._messages = []
        values = {
            "context": self.context, "form": RelationFixtureForm(),
            "records": records or [], "mandates": mandates or [], "relations": relations or [],
            "tree": [SimpleNamespace(
                name="Musterstadt", primary_parent=None,
                get_kind_display=lambda: "Gemeinde",
            )],
        }
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("registry.html", values, request=request)

    def test_records_and_mandates_keep_edit_paths_and_validity(self):
        record = SimpleNamespace(
            pk=uuid4(), name="Bauausschuss", archived=True, starts_on=date(2023, 1, 1),
            ends_on=date(2025, 12, 31), get_kind_display=lambda: "Gremium",
        )
        mandate = SimpleNamespace(
            pk=uuid4(), committee="Gemeinderat", function="Mitglied",
            user=SimpleNamespace(get_full_name=lambda: "Person Beispiel", email="person@example.invalid"),
            person=None, faction="Testfraktion", starts_on=date(2024, 1, 1),
            ends_on=None, substitutes_for=None, archived=False,
        )
        relation = SimpleNamespace(
            pk=42, target=SimpleNamespace(name="Zweckverband Beispiel"),
            description="Interkommunale Aufgabe", responsibility="Verwaltung",
            starts_on=None, ends_on=None,
        )
        html = self.render_registry([record], [mandate], [relation])
        for text in (
            "Gremien &amp; Stammdaten", "Bauausschuss", "Historisch archiviert",
            "Gemeinderat", "Person Beispiel", "Besetzung erfasst",
            "Zweckverband Beispiel", "Beziehungen anzeigen und verwalten",
            "keine", "Körperschaft und Hauptzuordnung",
        ):
            self.assertIn(text, html)
        self.assertIn(str(record.pk), html)
        self.assertIn(str(mandate.pk), html)
        self.assertIn(str(relation.pk), html)
        self.assertIn('name="mode"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('id="beziehungen"', html)

    def test_empty_states_still_offer_create_actions_and_relation_form(self):
        html = self.render_registry()
        self.assertIn("Das Register ist noch leer", html)
        self.assertIn("Noch keine Besetzungen erfasst", html)
        self.assertIn("Bisher sind keine zusätzlichen Organisationsbeziehungen", html)
        self.assertIn("Ersten Datensatz anlegen", html)
        self.assertIn("Erste Besetzung hinzufügen", html)
        self.assertIn('name="target"', html)
        self.assertIn('name="reason"', html)
