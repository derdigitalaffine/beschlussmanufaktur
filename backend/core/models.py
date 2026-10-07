import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    advanced_mode = models.BooleanField(default=False)
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
    advanced_enabled = models.BooleanField(default=True)
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
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    responsibility = models.CharField(max_length=200, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(source=models.F("target")), name="relation_not_self"),
            models.UniqueConstraint(fields=["source", "target", "description"], name="unique_relation"),
        ]


class Membership(models.Model):
    class Role(models.TextChoices):
        ORGANIZATION_ADMIN = "organization_admin", "Organisationsverwaltung"
        REVIEWER = "reviewer", "Fachbereichsleitung / Prüfung"
        RELEASE = "release", "Freigabe"
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


class RegistryRecord(models.Model):
    """Versioned municipal registry. Historical records are closed, never deleted."""
    class Kind(models.TextChoices):
        TERM = 'term', 'Legislaturperiode'
        COMMITTEE = 'committee', 'Gremium'
        UNIT = 'unit', 'Organisationseinheit'
        FUNCTION = 'function', 'Funktion'
        PERSON = 'person', 'Person ohne Konto'
        FACTION = 'faction', 'Fraktion'
        ROOM = 'room', 'Raum'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=200)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    details = models.TextField(blank=True, max_length=2000)
    version = models.PositiveIntegerField(default=1)
    archived = models.BooleanField(default=False)
    class Meta:
        ordering = ['kind', 'name', 'id']
        constraints = [models.CheckConstraint(condition=models.Q(starts_on__isnull=True) | models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=models.F('starts_on')), name='registry_period')]
    def clean(self):
        if self.kind == self.Kind.TERM and (not self.starts_on or not self.ends_on):
            raise ValidationError('Eine Legislaturperiode benötigt Beginn und Ende.')
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError('Das Ende darf nicht vor dem Beginn liegen.')
    def __str__(self):
        return self.name


class Mandate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    committee = models.ForeignKey(RegistryRecord, on_delete=models.PROTECT, related_name='mandates')
    term = models.ForeignKey(RegistryRecord, on_delete=models.PROTECT, related_name='term_mandates')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    person = models.ForeignKey(RegistryRecord, null=True, blank=True, on_delete=models.PROTECT, related_name='person_mandates')
    function = models.ForeignKey(RegistryRecord, on_delete=models.PROTECT, related_name='function_mandates')
    faction = models.ForeignKey(RegistryRecord, null=True, blank=True, on_delete=models.PROTECT, related_name='faction_mandates')
    substitutes_for = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField()
    voting = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(ends_on__gte=models.F('starts_on')), name='mandate_period'), models.CheckConstraint(condition=(models.Q(user__isnull=False, person__isnull=True) | models.Q(user__isnull=True, person__isnull=False)), name='mandate_identity')]
    def clean(self):
        if bool(self.user_id) == bool(self.person_id):
            raise ValidationError('Genau ein Konto oder eine Person auswählen.')
        for field, kind in [('committee','committee'),('term','term'),('person','person'),('function','function'),('faction','faction')]:
            obj = getattr(self, field, None)
            if obj and (obj.kind != kind or obj.organization_id != self.committee.organization_id):
                raise ValidationError('Gremium, Periode, Person und Funktionen müssen zur Körperschaft gehören.')
        if self.ends_on < self.starts_on:
            raise ValidationError('Ungültiger Zeitraum.')
        if self.substitutes_for_id and (self.substitutes_for_id == self.pk or self.substitutes_for.committee_id != self.committee_id or self.substitutes_for.term_id != self.term_id or self.substitutes_for.substitutes_for_id):
            raise ValidationError('Vertretung muss ein reguläres Mandat desselben Gremiums und derselben Periode betreffen.')


class AccessGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    membership = models.ForeignKey(Membership,on_delete=models.PROTECT)
    resource_kind = models.CharField(max_length=30,choices=[('organization','Körperschaft'),('registry','Gremium / Stammdatensatz'),('template','Vorlage'),('unit','Organisationseinheit')])
    resource_id = models.UUIDField()
    actions = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True,blank=True)
    revoked_at = models.DateTimeField(null=True,blank=True)
    reason = models.CharField(max_length=500)
    def clean(self):
        if self.membership.organization_id != self.organization_id:
            raise ValidationError('Die Zuweisung muss zur Körperschaft gehören.')
        if not isinstance(self.actions,list) or not self.actions or set(self.actions)-{'read','edit','review','release','publish','export','delegate'}:
            raise ValidationError('Unzulässige Einzelrechte.')
        if self.resource_kind=='organization':
            valid=self.resource_id==self.organization_id
        elif self.resource_kind in ('registry','unit'):
            valid=RegistryRecord.objects.filter(pk=self.resource_id,organization=self.organization).exists()
        else:
            # Template model is introduced by the next module.
            from django.apps import apps
            valid=apps.get_model('core','Template').objects.filter(pk=self.resource_id,organization=self.organization).exists()
        if not valid:raise ValidationError('Rechteobjekt gehört nicht zur Körperschaft.')
