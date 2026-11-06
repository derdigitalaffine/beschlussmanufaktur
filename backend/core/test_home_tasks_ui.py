from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from .home_tasks import today_tasks


def meeting(name):
    return SimpleNamespace(
        pk=uuid4(), title=name, starts_at=timezone.now() + timedelta(days=2),
        committee=SimpleNamespace(name="Hauptausschuss"), location="Rathaus",
    )


def decision(name, due):
    return SimpleNamespace(
        pk=uuid4(), status="in_progress", due_on=due,
        vote=SimpleNamespace(item=SimpleNamespace(title=name)),
    )


@override_settings(SERVER_ROLE="internal")
class TodayTasksUITests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(pk=uuid4(), is_authenticated=True)
        self.context = SimpleNamespace(
            organization=SimpleNamespace(name="Musterstadt"), user_id=self.user.pk,
        )

    def test_no_active_context_queries_no_data(self):
        with (
            patch("core.home_tasks.Meeting.objects.filter") as meetings,
            patch("core.home_tasks.Decision.objects.filter") as decisions,
        ):
            result = today_tasks(None, self.user)
            self.assertEqual(result["today_open_count"], 0)
            self.assertIsNone(result["today_next_meeting"])
            meetings.assert_not_called()
            decisions.assert_not_called()

    def test_only_readable_meeting_and_assigned_visible_decisions(self):
        denied_meeting, allowed_meeting = meeting("Geschützt"), meeting("Öffentliches Gremium")
        denied_task = decision("Fremder Beschluss", timezone.localdate() - timedelta(days=10))
        past_task = decision("Eigene Aufgabe", timezone.localdate() - timedelta(days=3))
        future_task = decision("Zweite Aufgabe", timezone.localdate() + timedelta(days=5))
        with (
            patch("core.home_tasks.Meeting.objects.filter") as meetings,
            patch("core.home_tasks.Decision.objects.filter") as decisions,
            patch("core.home_tasks.meeting_access", side_effect=lambda ctx, action, obj: obj is allowed_meeting),
            patch("core.decision_views.access", side_effect=lambda ctx, obj: obj is not denied_task),
        ):
            meetings.return_value.select_related.return_value.order_by.return_value.iterator.return_value = [
                denied_meeting, allowed_meeting,
            ]
            decisions.return_value.exclude.return_value.select_related.return_value.iterator.return_value = [
                future_task, denied_task, past_task,
            ]
            result = today_tasks(self.context, self.user)
        self.assertIs(result["today_next_meeting"], allowed_meeting)
        self.assertEqual(result["today_open_count"], 2)
        self.assertEqual([d.pk for d in result["today_decisions"]], [past_task.pk, future_task.pk])
        self.assertTrue(result["today_decisions"][0].overdue)
        self.assertFalse(result["today_decisions"][1].overdue)

    @override_settings(SERVER_ROLE="protected")
    def test_protected_server_does_not_read_internal_decision_data(self):
        item = meeting("Ratsversammlung")
        with (
            patch("core.home_tasks.Meeting.objects.filter") as meetings,
            patch("core.home_tasks.meeting_access", return_value=True),
            patch("core.home_tasks.Decision.objects.filter") as decisions,
        ):
            meetings.return_value.select_related.return_value.order_by.return_value.iterator.return_value = [item]
            result = today_tasks(self.context, self.user)
        self.assertIs(result["today_next_meeting"], item)
        self.assertEqual(result["today_decisions"], [])
        decisions.assert_not_called()
