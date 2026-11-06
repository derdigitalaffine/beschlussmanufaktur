from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve
from django.utils import timezone

from .decision_views import detail


def decision(status="reported"):
    obj = SimpleNamespace(
        pk=uuid4(), status=status, version=5, due_on=None,
        responsible=None, responsible_id=None,
        wording="Der Rat beschließt die Sanierung.", progress="Ausführung vorbereitet.",
        result={"counts":{"Ja":15,"Nein":3},"eligible":20,"invalid":0,"missing":2,"outcome":"accepted"},
        chair_confirmation="Mehrheit festgestellt.",
        vote=SimpleNamespace(
            meeting=SimpleNamespace(title="Gemeinderat", organization=SimpleNamespace(name="Musterstadt")),
            item=SimpleNamespace(title="Brückensanierung"),
        ),
    )
    obj.ui_status="Erledigung gemeldet" if status=="reported" else "Abgeschlossen"
    obj.ui_tone="info" if status=="reported" else "success"
    obj.overdue=False
    obj.updates=MagicMock()
    obj.updates.select_related.return_value.order_by.return_value=[]
    return obj


@override_settings(SERVER_ROLE="internal")
class DecisionDetailUITests(SimpleTestCase):
    def setUp(self):
        self.factory=RequestFactory()
        self.context=SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"),
            role="clerk", user_id=uuid4(), get_role_display=lambda: "Sitzungsdienst",
        )

    def render_detail(self, obj, **overrides):
        request=self.factory.get("/beschluesse/"+str(obj.pk)+"/")
        request.user=SimpleNamespace(is_authenticated=True, username="clerk", pk=self.context.user_id)
        request.resolver_match=resolve(request.path)
        request.session={}
        request._messages=[]
        kwargs={
            "context":self.context,"obj":obj,"manager":True,
            "can_progress":True,"can_close":True,"can_not_required":True,
            "can_reopen":False,"progress":obj.progress,"reason_value":"",
            "error":None,"memberships":[],"updates":[],
        }
        kwargs.update(overrides)
        with patch("core.shell.active_context", return_value=self.context):
            return render_to_string("decision.html",kwargs,request=request)

    def test_reported_action_is_separate_from_progress_save(self):
        html=self.render_detail(decision())
        for text in ("Brückensanierung", "Erledigung gemeldet", "Beschlossener Wortlaut",
                     "Sachstand speichern", "Erledigung melden", "Erledigung geprüft bestätigen",
                     "Feststellung des Vorsitzes", "15", "Nein"):
            self.assertIn(text,html)
        self.assertNotIn('value="reopen"',html)
        self.assertIn('value="close"',html)
        self.assertIn('required',html)
        self.assertIn('name="version"',html)
        self.assertIn('name="csrfmiddlewaretoken"',html)

    def test_read_only_user_sees_no_post_actions(self):
        html=self.render_detail(decision("closed"), manager=False, can_progress=False,
                                can_close=False, can_not_required=False, can_reopen=False)
        self.assertIn("Derzeit keine Sachstandänderung möglich",html)
        self.assertNotIn('name="action"',html)
        self.assertIn("Beschlossener Wortlaut",html)

    def test_closed_assignee_gets_no_progress_action_on_server(self):
        obj=decision("closed")
        obj.responsible_id=self.context.user_id
        request=self.factory.get("/beschluesse/"+str(obj.pk)+"/")
        request.user=SimpleNamespace(is_authenticated=True,pk=self.context.user_id)
        with (
            patch("core.decision_views.get_object_or_404",return_value=obj),
            patch("core.decision_views.active_context",return_value=self.context),
            patch("core.decision_views.access",return_value=True),
            patch("core.decision_views.meeting_access",return_value=False),
            patch("core.decision_views.Membership.objects.filter") as memberships,
            patch("core.decision_views.render") as rendered,
        ):
            memberships.return_value=[]
            detail(request,obj.pk)
            context=rendered.call_args.args[2]
            self.assertFalse(context["can_progress"])
            self.assertFalse(context["can_close"])
            self.assertFalse(context["can_reopen"])
