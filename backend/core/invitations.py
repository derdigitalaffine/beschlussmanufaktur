"""Organisation-scoped invitation and role mutations.

The organisation row serialises admin changes. New users are created only
after proof of invitation possession. Existing accounts must authenticate.
"""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AuditEvent, Invitation, Membership, Organization, User
from .permissions import available_contexts


def digest_token(token):
    return salted_hmac("organization-invitation", token, algorithm="sha256").hexdigest()


def usable_invitations():
    now = timezone.now()
    return Invitation.objects.filter(accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=now).exclude(ends_at__lte=now)


def invitation_for_token(token):
    if len(token) != 43:
        return None
    invitation = usable_invitations().select_related("organization", "invited_by").filter(token_digest=digest_token(token)).first()
    return invitation if invitation and inviter_authorized(invitation) else None


def inviter_authorized(invitation):
    return bool(invitation.invited_by and available_contexts(invitation.invited_by).filter(
        organization=invitation.organization, role=Membership.Role.ORGANIZATION_ADMIN,
    ).exists())


def lock_admin(actor, context_id, organization_id):
    organization = Organization.objects.select_for_update().get(pk=organization_id)
    if not available_contexts(actor).filter(pk=context_id, organization=organization, role=Membership.Role.ORGANIZATION_ADMIN).exists():
        raise PermissionDenied("Die Organisationsberechtigung ist nicht mehr gültig.")
    return organization


def check_existing_role(organization, email, role, exclude=None):
    memberships = Membership.objects.filter(organization=organization, user__email__iexact=email, role=role, revoked_at__isnull=True)
    memberships = memberships.exclude(ends_at__lte=timezone.now())
    if exclude:
        memberships = memberships.exclude(pk=exclude)
    if memberships.exists():
        raise ValidationError("Diese Rolle ist bereits zugewiesen. Bearbeiten Sie die bestehende Zuweisung.")


def create_invitation(actor, context, data):
    with transaction.atomic():
        organization = lock_admin(actor, context.pk, context.organization_id)
        check_existing_role(organization, data["email"], data["role"])
        if usable_invitations().filter(organization=organization, email=data["email"], role=data["role"]).exists():
            raise ValidationError("Für diese Rolle besteht bereits eine offene Einladung.")
        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            organization=organization, email=data["email"], role=data["role"], starts_at=data["starts_at"], ends_at=data["ends_at"],
            invited_by=actor, token_digest=digest_token(token), expires_at=timezone.now()+timedelta(days=7),
        )
        invitation.full_clean()
        invitation.save()
        link = f"{settings.APPLICATION_URL}/einladung/#{token}"
        send_mail("Einladung zur Beschlussmanufaktur", (
            f"Sie wurden für {organization.name} als {invitation.get_role_display()} eingeladen.\n\n"
            f"Einladung öffnen: {link}\n\nEinladungscode: {token}\n\n"
            "Der Link gilt sieben Tage. Bereits bestehende Konten melden sich zur Annahme an. "
            "Neue Konten legen ihr Passwort selbst fest. Geben Sie den Einladungscode nicht weiter."
        ), None, [invitation.email])
        AuditEvent.objects.create(actor=actor, action="invitation.sent", object_id=str(invitation.pk), metadata={"organization": str(organization.pk), "role": invitation.role})
        return invitation


def accept_invitation(invitation_id, authenticated_user, account_data=None):
    with transaction.atomic():
        initial = usable_invitations().filter(pk=invitation_id).first()
        if not initial:
            raise ValidationError("Diese Einladung ist nicht mehr gültig.")
        # Same lock order as all admin mutations: organisation, then invitation.
        Organization.objects.select_for_update().get(pk=initial.organization_id)
        invitation = usable_invitations().select_for_update().filter(pk=invitation_id).first()
        if not invitation:
            raise ValidationError("Diese Einladung ist nicht mehr gültig.")
        if not inviter_authorized(invitation):
            raise ValidationError("Diese Einladung ist nicht mehr freigegeben. Bitten Sie Ihre Administration um eine neue Einladung.")
        user = User.objects.filter(email__iexact=invitation.email).first()
        if user:
            if not authenticated_user.is_authenticated or authenticated_user.pk != user.pk or not user.is_active:
                raise PermissionDenied("Melden Sie sich mit dem eingeladenen Konto an.")
        else:
            if account_data is None or authenticated_user.is_authenticated:
                raise PermissionDenied("Für dieses neue Konto ist eine eigene Einrichtung erforderlich.")
            user = User(username=str(uuid.uuid4()), email=invitation.email,
                first_name=account_data["first_name"], last_name=account_data["last_name"])
            validate_password(account_data["password"], user)
            user.set_password(account_data["password"])
            user.full_clean()
            user.save()
        check_existing_role(invitation.organization, invitation.email, invitation.role)
        membership = Membership.objects.create(user=user, organization=invitation.organization, role=invitation.role,
            starts_at=invitation.starts_at, ends_at=invitation.ends_at)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        AuditEvent.objects.create(actor=user, action="invitation.accepted", object_id=str(invitation.pk), metadata={"membership": str(membership.pk)})
        return membership


def protect_last_admin(membership, data=None):
    now = timezone.now()
    is_active_admin = membership.role == Membership.Role.ORGANIZATION_ADMIN and membership.starts_at <= now and not membership.revoked_at and (not membership.ends_at or membership.ends_at > now)
    keeps_admin = data and data["role"] == Membership.Role.ORGANIZATION_ADMIN and data["starts_at"] <= now and (not data["ends_at"] or data["ends_at"] > now)
    if is_active_admin and not keeps_admin:
        others = Membership.objects.filter(organization=membership.organization, user__is_active=True,
            role=Membership.Role.ORGANIZATION_ADMIN, starts_at__lte=now, revoked_at__isnull=True).exclude(pk=membership.pk).exclude(ends_at__lte=now)
        if not others.exists():
            raise ValidationError("Die letzte aktive Organisationsverwaltung darf nicht entfernt werden. Weisen Sie zuerst eine weitere zu.")


def change_membership(actor, context, membership_id, data, reason):
    with transaction.atomic():
        organization = lock_admin(actor, context.pk, context.organization_id)
        membership = Membership.objects.select_for_update().get(pk=membership_id, organization=organization)
        if membership.version != data["version"]:
            raise ValidationError("Diese Rolle wurde zwischenzeitlich geändert. Laden Sie die Seite neu und prüfen Sie den aktuellen Stand.")
        if membership.revoked_at:
            raise ValidationError("Eine entzogene Rolle kann nicht reaktiviert werden. Versenden Sie eine neue Einladung.")
        protect_last_admin(membership, data)
        check_existing_role(organization, membership.user.email, data["role"], exclude=membership.pk)
        before = {"role": membership.role, "starts_at": membership.starts_at.isoformat(), "ends_at": membership.ends_at.isoformat() if membership.ends_at else None}
        membership.role, membership.starts_at, membership.ends_at = data["role"], data["starts_at"], data["ends_at"]
        membership.full_clean()
        membership.version += 1
        membership.save(update_fields=["role", "starts_at", "ends_at", "version"])
        after = {"role": membership.role, "starts_at": membership.starts_at.isoformat(), "ends_at": membership.ends_at.isoformat() if membership.ends_at else None}
        AuditEvent.objects.create(actor=actor, action="membership.changed", object_id=str(membership.pk), metadata={"reason": reason, "before": before, "after": after, "organization": str(organization.pk)})


def revoke_membership(actor, context, membership_id, reason, version):
    with transaction.atomic():
        organization = lock_admin(actor, context.pk, context.organization_id)
        membership = Membership.objects.select_for_update().get(pk=membership_id, organization=organization)
        if membership.version != version:
            raise ValidationError("Diese Rolle wurde zwischenzeitlich geändert. Laden Sie die Seite neu und prüfen Sie den aktuellen Stand.")
        protect_last_admin(membership)
        if not membership.revoked_at:
            membership.revoked_at = timezone.now()
            membership.version += 1
            membership.save(update_fields=["revoked_at", "version"])
            AuditEvent.objects.create(actor=actor, action="membership.revoked", object_id=str(membership.pk), metadata={"reason": reason})


def revoke_invitation(actor, context, invitation_id, reason):
    with transaction.atomic():
        organization = lock_admin(actor, context.pk, context.organization_id)
        invitation = Invitation.objects.select_for_update().get(pk=invitation_id, organization=organization)
        if invitation.accepted_at:
            raise ValidationError("Diese Einladung wurde angenommen. Entziehen Sie bei Bedarf die zugewiesene Rolle.")
        if not invitation.revoked_at:
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=["revoked_at"])
            AuditEvent.objects.create(actor=actor, action="invitation.revoked", object_id=str(invitation.pk), metadata={"reason": reason})
