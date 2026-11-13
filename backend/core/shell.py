"""Leichtgewichtiger, serverseitig bestimmter Arbeitskontext für die App-Shell.

Die Navigation gewährt keine Zugriffsrechte. Jede Fachansicht prüft weiterhin
serverseitig ihre eigenen Berechtigungen.
"""
from django.conf import settings

from .permissions import active_context, may_manage_organization



# Navigation reflects the current *location*; it does not grant any permission.
# Nested detail/editor routes highlight their parent work area.
def _navigation_section(route):
    if route == "home":
        return "home"
    if route in {"templates", "replica_documents", "kind_list"} or route.startswith(
        ("template_", "kind_", "replica_document", "replica_export", "replica_propose",
         "consultation_", "attachment_", "notification_")
    ):
        return "templates"
    if route in {"meetings", "minutes", "votes", "session_returns"} or route.startswith(
        ("meeting_", "live_", "vote_", "minutes_", "invitation_", "session_")
    ):
        return "meetings"
    if route in {"decisions", "decision"} or route.startswith("decision_"):
        return "decisions"
    if route in {"member_desk", "personal_note"}:
        return "member_desk"
    if route in {"registry", "structure", "relation_edit", "mode"} or route.startswith("registry_"):
        return "registry"
    if route in {"users", "grants", "revoke_grant", "person_profiles",
                 "person_profile", "person_identities", "sample_data", "imports",
                 "import_detail", "exchange", "review_remote"} or route.startswith(
        ("membership_", "edit_membership", "remove_membership", "remove_invitation")
    ):
        return "users"
    return None

def workspace_shell(request):
    """Stellt nur den aktuell gültigen Kontext der angemeldeten Person bereit."""
    if settings.SERVER_ROLE == "public" or not request.user.is_authenticated:
        return {"shell_context": None, "shell_internal": False, "shell_can_manage": False}
    context = active_context(request)
    route = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""
    section = _navigation_section(route)
    query = request.GET.get("q", "")[:100] if route == "member_desk" else ""
    return {
        "shell_context": context,
        "shell_active_section": section,
        "shell_search_query": query,
        "shell_internal": settings.SERVER_ROLE == "internal",
        "shell_can_manage": settings.SERVER_ROLE == "internal" and may_manage_organization(context),
    }
