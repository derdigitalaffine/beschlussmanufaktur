from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve


@override_settings(SERVER_ROLE="internal")
class TemplateDetailUITests(SimpleTestCase):
    def setUp(self):
        self.factory=RequestFactory()
        self.context=SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="author", get_role_display=lambda: "Sachbearbeitung",
        )

    def render_detail(self,state):
        obj=SimpleNamespace(
            pk=uuid4(), subject="Vorlage zur Brückensanierung",
            kind="Beschlussvorlage", number="", state=state, version=3,
            get_classification_display=lambda: "Gremienkreis",
            ui_status={"review":"In Prüfung","returned":"Zurückgegeben","ready":"Bereitgestellt"}.get(state,"Entwurf"),
            ui_tone="attention" if state=="returned" else "info",
            reference="", unit=None, fields={},
        )
        request=self.factory.get("/vorlagen/"+str(obj.pk)+"/")
        request.user=SimpleNamespace(is_authenticated=True, username="person", first_name="Erika")
        request.resolver_match=resolve(request.path)
        request.session={}
        request._messages=[]
        values={
            "context":self.context,"obj":obj,"body":"Ein fachlicher Vorlagentext.",
            "steps":[],"can_publish":False,"can_edit":True,"can_delegate":False,
            "versions":[],"comments":[],"attachments":[],"presence":[],
            "eligible":[],"consultations":[],"committees":[],
        }
        with patch("core.shell.active_context",return_value=self.context):
            return render_to_string("template_detail.html",values,request=request)

    def test_review_state_shows_version_context_and_no_duplicate_submit(self):
        html=self.render_detail("review")
        for text in ("Vorlage zur Brückensanierung","In Prüfung","Fassung 3",
                     "Prüfstand ansehen","Prüfung und Bereitstellung",
                     "Ausgaben und Veröffentlichung","Zusammenarbeit und Aufgaben",
                     "Anlagen","Beratungsfolge","Versionen"):
            self.assertIn(text,html)
        self.assertIn('id="pruefung"',html)
        self.assertIn('aria-current="step"',html)
        self.assertNotIn("Diese Fassung zur Prüfung geben",html)

    def test_returned_state_explains_reason_and_retains_submit_path(self):
        html=self.render_detail("returned")
        self.assertIn("zurückgegeben",html)
        self.assertIn("Diese Fassung zur Prüfung geben",html)
        self.assertIn("Vorlage bearbeiten",html)
