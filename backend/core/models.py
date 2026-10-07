import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    last_context = models.ForeignKey("Membership", null=True, blank=True, on_delete=models.SET_NULL, related_name="remembered_by")

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="user_email_case_insensitive")]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Organization(models.Model):
    class Kind(models.TextChoices):
        ADMINISTRATION = "administration", "Verwaltungsverbund"
        DISTRICT = "district", "Landkreis"
        ASSOCIATION = "association", "Verbandsgemeinde"
        MUNICIPALITY = "municipality", "Ortsgemeinde"
        UNION = "union", "Zweckverband"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    primary_parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    created_at = models.DateTimeField(auto_now_add=True)
    is_test_data = models.BooleanField(default=False)

    class Meta:
        ordering = ["name", "id"]

    def clean(self):
        seen = {self.pk}
        parent = self.primary_parent
        while parent:
            if parent.pk in seen:
                raise ValidationError({"primary_parent": "Die Hauptstruktur darf keinen Kreis enthalten."})
            seen.add(parent.pk)
            parent = parent.primary_parent

    def __str__(self):
        return self.name


class OrganizationRelation(models.Model):
    source = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="outgoing_relations")
    target = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="incoming_relations")
    description = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(source=models.F("target")), name="relation_not_self"),
            models.UniqueConstraint(fields=["source", "target", "description"], name="unique_relation"),
        ]


class Membership(models.Model):
    class Role(models.TextChoices):
        ORGANIZATION_ADMIN = "organization_admin", "Organisationsverwaltung"
        CLERK = "clerk", "Sitzungsdienst"
        AUTHOR = "author", "Sachbearbeitung"
        CHAIR = "chair", "Vorsitz"
        MAYOR = "mayor", "Bürgermeister"
        LOCAL_MAYOR = "local_mayor", "Ortsbürgermeister"
        MEMBER = "member", "Mandatsträger"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=30, choices=Role.choices)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F("starts_at")), name="membership_valid_period",
        )]


class EmailChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True)


class LoginRateLimit(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window_start = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)


class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict)


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=30, choices=Membership.Role.choices)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(
            condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F("starts_at")),
            name="invitation_valid_membership_period",
        )]
