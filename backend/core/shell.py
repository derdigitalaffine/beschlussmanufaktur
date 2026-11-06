"""Leichtgewichtiger, serverseitig bestimmter Arbeitskontext für die App-Shell.

Die Navigation gewährt keine Zugriffsrechte. Jede Fachansicht prüft weiterhin
serverseitig ihre eigenen Berechtigungen.
"""
from django.conf import settings

from .permissions import active_context, may_manage_organization


def workspace_shell(request):
    """Stellt nur den aktuell gültigen Kontext der angemeldeten Person bereit."""
    if settings.SERVER_ROLE == "public" or not request.user.is_authenticated:
        return {"shell_context": None, "shell_internal": False, "shell_can_manage": False}
    context = active_context(request)
    return {
        "shell_context": context,
        "shell_internal": settings.SERVER_ROLE == "internal",
        "shell_can_manage": settings.SERVER_ROLE == "internal" and may_manage_organization(context),
    }
