from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django import forms
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


class EditorFixtureForm(forms.Form):
    subject = forms.CharField(label="Betreff", max_length=300)
    reference = forms.CharField(label="Aktenzeichen", required=False)
    classification = forms.ChoiceField(label="Empfängerkreis", choices=[("internal", "Verwaltungsintern")])
    unit = forms.CharField(label="Fachbereich", required=False)
    markdown = forms.CharField(label="Vorlagentext", widget=forms.Textarea(attrs={"data-editor": "true"}))
    public_markdown = forms.CharField(label="Öffentliche Fassung", required=False, widget=forms.Textarea(attrs={"data-editor": "true"}))
    extra_finance = forms.CharField(label="Finanzangaben", required=False)
    reason = forms.CharField(label="Änderungsgrund")
    expected_version = forms.IntegerField(widget=forms.HiddenInput)


@override_settings(SERVER_ROLE="internal")
class TemplateEditorUITests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="author", get_role_display=lambda: "Sachbearbeitung",
        )

    def render_editor(self, form, obj=None):
        request = self.factory.get("/vorlagen/neu/")
        request.user = SimpleNamespace(is_authenticated=True, username="tester", first_name="Erika")
        request.resolver_match = resolve(request.path)
        request.session = {}
        request._messages = []
        values = {
            "form": form, "obj": obj, "context": self.context,
            "kind": SimpleNamespace(name="Beschlussvorlage", fields=[{"key": "finance"}]),
            "kinds": [], "default_kinds": ["Beschlussvorlage"], "selection": "default:Beschlussvorlage",
        }
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("template_edit.html", values, request=request)

    def test_editor_keeps_hidden_version_and_all_field_sections(self):
        html = self.render_editor(EditorFixtureForm(initial={"expected_version": 2}))
        for label in (
            "Fachliche Angaben", "Vorlagentext", "Gesonderte öffentliche Fassung",
            "Weitere Fachangaben", "Fassung dokumentieren und speichern",
            "Finanzangaben", "Änderungsgrund",
        ):
            self.assertIn(label, html)
        self.assertIn('name="expected_version"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('name="kind"', html)
        self.assertIn('value="default:Beschlussvorlage" selected', html)
        self.assertIn('data-editor="true"', html)
        self.assertIn('name="public_markdown"', html)
        self.assertNotIn("novalidate", html)

    def test_validation_errors_are_identified_and_input_is_preserved(self):
        form = EditorFixtureForm(data={
            "subject": "", "reference": "A-42", "classification": "internal",
            "markdown": "Unverlorener Entwurfstext",
            "public_markdown": "Nur geprüfte öffentliche Fassung",
            "reason": "", "expected_version": "3",
        })
        self.assertFalse(form.is_valid())
        html = self.render_editor(form)
        self.assertIn("Eingaben prüfen", html)
        self.assertIn('role="alert"', html)
        self.assertIn('href="#id_subject"', html)
        self.assertIn("Unverlorener Entwurfstext", html)
        self.assertIn("Nur geprüfte öffentliche Fassung", html)

    def test_edit_form_retains_presence_and_returns_to_original(self):
        obj = SimpleNamespace(pk=uuid4(), version=3)
        html = self.render_editor(EditorFixtureForm(initial={"expected_version": 3}), obj=obj)
        self.assertIn("Bearbeitungsanzeige wird verbunden", html)
        self.assertIn("Neue Fassung speichern", html)
        self.assertIn("/vorlagen/" + str(obj.pk) + "/", html)
