from django.db.models import Q
from django.utils import timezone
from .models import Membership, AccessGrant, Mandate, ExchangeState
from django.conf import settings
from datetime import timedelta


def available_contexts(user):
    if not user.is_authenticated or not user.is_active:
        return Membership.objects.none()
    now = timezone.now()
    if settings.SERVER_ROLE == "protected" and not ExchangeState.objects.filter(channel="protected",received_at__gte=now-timedelta(seconds=settings.EXCHANGE_MAX_AGE)).exists():
        return Membership.objects.none()
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



MANDATE_ROLES=('member','chair','mayor','local_mayor')

def can_access(context, action, kind, obj):
    if not context or not available_contexts(context.user).filter(pk=context.pk).exists():return False
    organization_id = obj.pk if kind=='organization' else obj.organization_id
    if context.organization_id != organization_id:return False
    now=timezone.now()
    grants=AccessGrant.objects.filter(membership=context,resource_kind=kind,resource_id=obj.pk,revoked_at__isnull=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=now))
    organization_grants=AccessGrant.objects.filter(membership=context,resource_kind='organization',resource_id=organization_id,revoked_at__isnull=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=now))
    if any(action in grant.actions for grant in list(grants)+list(organization_grants)):return True
    if kind=='registry' and action in ('read','export') and context.role in MANDATE_ROLES:
        today=timezone.localdate()
        return Mandate.objects.filter(user=context.user,committee=obj,archived=False,starts_on__lte=today,ends_on__gte=today).exists()
    return False
