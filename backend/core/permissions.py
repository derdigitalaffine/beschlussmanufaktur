from django.db.models import Q
from django.utils import timezone
from .models import Membership


def available_contexts(user):
    if not user.is_authenticated or not user.is_active:
        return Membership.objects.none()
    now = timezone.now()
    return user.memberships.filter(starts_at__lte=now, revoked_at__isnull=True).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gt=now),
    ).select_related("organization").order_by("organization__name", "role", "id")


def active_context(request):
    remembered = request.session.get("context_id") or request.user.last_context_id
    if not remembered:
        return None
    return available_contexts(request.user).filter(pk=remembered).first()


def may_manage_organization(context):
    # Technical superusers do not implicitly gain access to municipal content.
    return bool(context and context.role == Membership.Role.ORGANIZATION_ADMIN)

