"""Kleine, ausschließlich lesende Prioritäten für den heutigen Arbeitskontext.

Die Widgets berechnen keine Fachrechte und geben keine Nutzeraufgaben über
Organisationsgrenzen hinweg aus: bestehende Service-Prüfungen entscheiden.
"""
from django.conf import settings
from django.utils import timezone

from .meetings_service import meeting_access
from .models import Decision, Meeting


def today_tasks(context, user):
    """Nächsten zugänglichen Termin und höchstens vier eigene offene Beschlüsse liefern."""
    result = {"today_next_meeting": None, "today_decisions": [], "today_open_count": 0}
    if context is None or settings.SERVER_ROLE == "public":
        return result

    # Sitzung nur anzeigen, wenn die gegenwärtige Fachberechtigung das Lesen erlaubt.
    meetings = (
        Meeting.objects.filter(organization=context.organization, starts_at__gte=timezone.now())
        .select_related("committee")
        .order_by("starts_at")
    )
    for meeting in meetings.iterator(chunk_size=100):
        if meeting_access(context, "read", meeting):
            result["today_next_meeting"] = meeting
            break

    if settings.SERVER_ROLE != "internal":
        return result

    from .decision_views import access

    # Vorfilter reduziert die Leselast; entscheidend ist weiterhin die Fachzugriffsprüfung.
    candidates = (
        Decision.objects.filter(
            vote__meeting__organization=context.organization, responsible=user,
        )
        .exclude(status__in=("closed", "not_required"))
        .select_related("vote__meeting", "vote__item", "responsible")
    )
    today = timezone.localdate()
    readable = []
    for decision in candidates.iterator(chunk_size=100):
        if not access(context, decision):
            continue
        decision.overdue = bool(decision.due_on and decision.due_on < today)
        readable.append(decision)
    readable.sort(key=lambda obj: (
        not obj.overdue, obj.due_on is None, obj.due_on or timezone.datetime.max.date(), str(obj.pk)
    ))
    result["today_decisions"] = readable[:4]
    result["today_open_count"] = len(readable)
    return result
