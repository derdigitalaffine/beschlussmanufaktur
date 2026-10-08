import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    exchange_managed = models.BooleanField(default=False)
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
        EMERGENCY = "emergency", "Befristeter Notfallzugriff"
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


class ExchangePolicy(models.Model):
    organization = models.OneToOneField(Organization,on_delete=models.PROTECT,primary_key=True)
    protected_enabled = models.BooleanField(default=False)
    public_enabled = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True)
    approved_by = models.ForeignKey(User,null=True,on_delete=models.SET_NULL)


class ExchangeState(models.Model):
    channel = models.CharField(max_length=20,primary_key=True)
    revision = models.PositiveBigIntegerField(default=0)
    received_at = models.DateTimeField(null=True)


class ExchangeNonce(models.Model):
    digest = models.CharField(max_length=64,primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TransferBatch(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    channel = models.CharField(max_length=20)
    revision = models.PositiveBigIntegerField()
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=200,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['channel','revision'],name='unique_exchange_revision')]


class RemoteChange(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization_id = models.UUIDField()
    resource_id = models.UUIDField()
    resource_kind = models.CharField(max_length=20,default='registry')
    base_version = models.PositiveIntegerField()
    context_id = models.UUIDField(null=True,blank=True)
    actor_id = models.PositiveBigIntegerField()
    content = models.TextField(max_length=100000)
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20,default='pending')
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True)


class PublicRecord(models.Model):
    id = models.UUIDField(primary_key=True)
    organization_id = models.UUIDField()
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=300)
    attachments = models.JSONField(default=list,blank=True)
    metadata = models.JSONField(default=dict,blank=True)
    body = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)


class TemplateKind(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    fields = models.JSONField(default=list,blank=True)
    initial_markdown = models.TextField(blank=True,max_length=100000)
    workflow = models.JSONField(default=list,blank=True)
    four_eyes = models.BooleanField(default=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['organization','name'],name='unique_template_kind')]
    def clean(self):
        from .templates_service import validate_configuration
        validate_configuration(self.fields,self.workflow)
    def __str__(self):return self.name


class Template(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    kind = models.ForeignKey(TemplateKind,on_delete=models.PROTECT)
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    subject = models.CharField(max_length=300)
    markdown = models.TextField(max_length=100000)
    public_markdown = models.TextField(blank=True,max_length=100000)
    fields = models.JSONField(default=dict,blank=True)
    unit = models.ForeignKey(RegistryRecord,null=True,blank=True,on_delete=models.PROTECT)
    reference = models.CharField(max_length=200,blank=True)
    classification = models.CharField(max_length=20,choices=[('internal','Verwaltungsintern'),('committee','Gremienkreis'),('restricted','Eingeschränkter Personenkreis'),('public_planned','Öffentlich vorgesehen')],default='internal')
    state = models.CharField(max_length=20,default='draft')
    version = models.PositiveIntegerField(default=1)
    number = models.CharField(max_length=40,blank=True)
    number_year = models.PositiveIntegerField(null=True,blank=True)
    number_sequence = models.PositiveIntegerField(null=True,blank=True)
    published_version = models.PositiveIntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-updated_at']
        constraints=[models.UniqueConstraint(fields=['organization','number_year','number_sequence'],name='unique_template_number')]
    def clean(self):
        if self.kind.organization_id!=self.organization_id:raise ValidationError('Vorlagenart gehört zu einer anderen Körperschaft.')
        if self.unit and (self.unit.organization_id!=self.organization_id or self.unit.kind!='unit'):raise ValidationError('Unzulässiger Fachbereich.')
    def __str__(self):return self.subject


class TemplateVersion(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='versions')
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    digest = models.CharField(max_length=64)
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['template','version'],name='unique_template_version')]
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Archivierte Fassungen sind unveränderlich.')
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError('Archivierte Fassungen bleiben erhalten.')


class TemplateParticipant(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='participants')
    membership = models.ForeignKey(Membership,on_delete=models.PROTECT)
    actions = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True,blank=True)
    revoked_at = models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['template','membership'],name='unique_template_participant')]


class Consultation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='consultations')
    committee = models.ForeignKey(RegistryRecord,on_delete=models.PROTECT)
    position = models.PositiveIntegerField(default=1)
    deciding = models.BooleanField(default=False)
    public = models.BooleanField(default=True)
    may_amend = models.BooleanField(default=False)
    amendment = models.TextField(blank=True,max_length=100000)
    version = models.PositiveIntegerField(default=1)
    class Meta:ordering=['position','id']


class TemplateLink(models.Model):
    source = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='links')
    target = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='backlinks')
    description = models.CharField(max_length=200)


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='attachments')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='attachments/%Y/%m')
    digest = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    media_type = models.CharField(max_length=100)
    public = models.BooleanField(default=False)
    checked = models.BooleanField(default=False)
    removed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TemplateComment(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='comments')
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    text = models.TextField(max_length=4000)
    version = models.PositiveIntegerField()
    task_assignee = models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT,related_name='template_tasks')
    completed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    path = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True)
    emailed_at = models.DateTimeField(null=True)


class EditPresence(models.Model):
    template = models.ForeignKey(Template,on_delete=models.CASCADE)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    seen_at = models.DateTimeField(default=timezone.now)
    class Meta:constraints=[models.UniqueConstraint(fields=['template','user'],name='unique_edit_presence')]


class ReviewStep(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT,related_name='review_steps')
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=30)
    substitute = models.CharField(max_length=30,blank=True)
    group = models.PositiveIntegerField()
    assigned = models.ForeignKey(Membership,null=True,blank=True,on_delete=models.PROTECT)
    state = models.CharField(max_length=20,default='pending')
    decided_by = models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    decided_at = models.DateTimeField(null=True)
    comment = models.CharField(max_length=1000,blank=True)


class NumberSequence(models.Model):
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    year = models.PositiveIntegerField()
    value = models.PositiveIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=['organization','year'],name='unique_number_sequence')]


class Publication(models.Model):
    template = models.ForeignKey(Template,on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    subject = models.CharField(max_length=300)
    markdown = models.TextField(max_length=100000)
    approved_by = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True)


class ExternalDocument(models.Model):
    id = models.UUIDField(primary_key=True)
    organization_id = models.UUIDField()
    title = models.CharField(max_length=300)
    markdown = models.TextField()
    number = models.CharField(max_length=40,blank=True)
    version = models.PositiveIntegerField()
    permissions = models.JSONField(default=dict)
    attachments = models.JSONField(default=list)
    received_at = models.DateTimeField(default=timezone.now)


class ReplicaAsset(models.Model):
    id = models.UUIDField(primary_key=True)
    digest = models.CharField(max_length=64)
    data = models.BinaryField()
    received_at = models.DateTimeField(auto_now=True)


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    committee = models.ForeignKey(RegistryRecord,on_delete=models.PROTECT,related_name='meetings')
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    room = models.ForeignKey(RegistryRecord,null=True,blank=True,on_delete=models.PROTECT,related_name='room_meetings')
    location = models.CharField(max_length=300)
    chair = models.ForeignKey(User,on_delete=models.PROTECT,related_name='chaired_meetings')
    scribe = models.ForeignKey(User,on_delete=models.PROTECT,related_name='scribed_meetings')
    created_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='created_meetings')
    paused = models.BooleanField(default=False)
    state = models.CharField(max_length=30,default='preparation')
    version = models.PositiveIntegerField(default=1)
    rules = models.JSONField(default=dict,blank=True)
    statutory_count = models.PositiveIntegerField(default=1)
    invitation_days = models.PositiveIntegerField(default=4)
    proposal_deadline = models.DateTimeField(null=True,blank=True)
    release_deadline = models.DateTimeField(null=True,blank=True)
    public_notice = models.TextField(blank=True,max_length=10000)
    public_enabled = models.BooleanField(default=False)
    authority_base = models.PositiveIntegerField(default=0)
    permission_snapshot = models.JSONField(default=dict,blank=True)
    leading_server = models.CharField(max_length=20,default='internal')
    active_item = models.ForeignKey('AgendaItem',null=True,blank=True,on_delete=models.PROTECT,related_name='+')
    class Meta:ordering=['starts_at','id']
    def clean(self):
        if self.committee_id and (self.committee.kind!='committee' or self.committee.organization_id!=self.organization_id):raise ValidationError('Gremium gehört nicht zur Körperschaft.')
        if self.room and (self.room.kind!='room' or self.room.organization_id!=self.organization_id):raise ValidationError('Raum gehört nicht zur Körperschaft.')
        if self.ends_at and self.starts_at and self.ends_at<=self.starts_at:raise ValidationError('Sitzungsende muss nach Beginn liegen.')
        if self.statutory_count<1:raise ValidationError('Gesetzliche Mitgliederzahl erforderlich.')
        for person_id in (self.chair_id,self.scribe_id):
            if person_id and not Membership.objects.filter(user_id=person_id,organization=self.organization).exists():raise ValidationError('Vorsitz und Schriftführung brauchen einen zugehörigen Arbeitskontext.')


class AgendaItem(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='items')
    parent = models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='subitems')
    position = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=300)
    public_title = models.CharField(max_length=300,blank=True)
    public = models.BooleanField(default=True)
    template = models.ForeignKey(Template,null=True,blank=True,on_delete=models.PROTECT)
    markdown = models.TextField(blank=True,max_length=100000)
    frozen_template = models.JSONField(default=dict,blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True,blank=True)
    proposed_by = models.ForeignKey(User,on_delete=models.PROTECT)
    removed = models.BooleanField(default=False)
    class Meta:ordering=['position','id']
    def clean(self):
        parent=self.parent;seen={self.pk}
        while parent:
            if parent.pk in seen or parent.meeting_id!=self.meeting_id:raise ValidationError('Ungültige TOP-Untergliederung.')
            seen.add(parent.pk);parent=parent.parent
        if self.position<1:raise ValidationError('Reihenfolge beginnt bei 1.')
        if not self.public and not self.public_title.strip():raise ValidationError('Nichtöffentlicher TOP benötigt einen unverfänglichen Bekanntmachungstitel.')


class MeetingInvitation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='invitations')
    revision = models.PositiveIntegerField()
    snapshot = models.JSONField()
    digest = models.CharField(max_length=64)
    reason = models.CharField(max_length=1000,blank=True)
    issued_by = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['meeting','revision'],name='unique_meeting_invitation')]
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Versandstände sind unveränderlich.')
        super().save(*args,**kwargs)


class InvitationDelivery(models.Model):
    invitation = models.ForeignKey(MeetingInvitation,on_delete=models.PROTECT,related_name='deliveries')
    user = models.ForeignKey(User,on_delete=models.PROTECT)
    snapshot = models.JSONField()
    delivered_at = models.DateTimeField(null=True,blank=True)
    seen_at = models.DateTimeField(null=True,blank=True)
    error = models.CharField(max_length=200,blank=True)
    attempts = models.PositiveIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=['invitation','user'],name='unique_invitation_delivery')]


class MeetingGuest(models.Model):
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    membership = models.ForeignKey(Membership,on_delete=models.PROTECT)
    expires_at = models.DateTimeField()
    private = models.BooleanField(default=False)
    class Meta:constraints=[models.UniqueConstraint(fields=['meeting','membership'],name='unique_meeting_guest')]


class MeetingAmendment(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    base_version = models.PositiveIntegerField()
    kind = models.CharField(max_length=30,choices=[('correction','Berichtigung'),('urgent','Dringlicher neuer Gegenstand'),('attachment','Zusätzliche Unterlage'),('remove','Gegenstand absetzen'),('reschedule','Termin ändern')])
    reason = models.CharField(max_length=1000)
    data = models.JSONField()
    requested_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='meeting_amendments')
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.PROTECT)
    state = models.CharField(max_length=20,default='pending')
    decision_record = models.CharField(max_length=1000,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MeetingParticipant(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='roster')
    user = models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT)
    person = models.ForeignKey(RegistryRecord,null=True,blank=True,on_delete=models.PROTECT)
    mandate = models.ForeignKey(Mandate,null=True,blank=True,on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    function = models.CharField(max_length=200,blank=True)
    voting = models.BooleanField(default=False)
    present = models.BooleanField(default=False)
    substitutes_for = models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['meeting','user'],name='unique_meeting_user'),models.UniqueConstraint(fields=['meeting','person'],name='unique_meeting_person')]


class MeetingLease(models.Model):
    meeting = models.OneToOneField(Meeting,on_delete=models.PROTECT,primary_key=True)
    holder = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    device = models.UUIDField()
    epoch = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField()


class MeetingEvent(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='events')
    item = models.ForeignKey(AgendaItem,null=True,blank=True,on_delete=models.PROTECT)
    kind = models.CharField(max_length=30)
    payload = models.JSONField(default=dict,blank=True)
    digest = models.CharField(max_length=64)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    device = models.UUIDField()
    occurred_at = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    class Meta:ordering=['version','id']
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Ereignisse sind unveränderlich; Korrektur als neues Ereignis erfassen.')
        super().save(*args,**kwargs)


class ConflictOfInterest(models.Model):
    participant = models.ForeignKey(MeetingParticipant,on_delete=models.PROTECT)
    item = models.ForeignKey(AgendaItem,on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    reason = models.CharField(max_length=1000)
    class Meta:constraints=[models.UniqueConstraint(fields=['participant','item'],name='unique_item_conflict')]


class ItemNote(models.Model):
    item = models.OneToOneField(AgendaItem,on_delete=models.PROTECT,primary_key=True)
    markdown = models.TextField(max_length=100000,blank=True)


class Motion(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    item = models.ForeignKey(AgendaItem,on_delete=models.PROTECT,related_name='motions')
    applicant = models.CharField(max_length=200)
    wording = models.TextField(max_length=100000)
    kind = models.CharField(max_length=30,choices=[('substantive','Sachantrag'),('amendment','Änderungsantrag'),('procedure','Geschäftsordnungsantrag')])
    position = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=30,default='pending')


class Vote(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='votes')
    item = models.ForeignKey(AgendaItem,on_delete=models.PROTECT)
    wording = models.TextField(max_length=100000)
    mode = models.CharField(max_length=20,choices=[('manual','Handzeichen / Papier'),('named','Digitale namentliche Abstimmung'),('secret','Geheime Papierwahl')])
    rule = models.CharField(max_length=30,default='majority_cast')
    options = models.JSONField(default=list)
    electorate = models.JSONField(default=list)
    state = models.CharField(max_length=20,default='open')
    result = models.JSONField(default=dict,blank=True)
    opened_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Ballot(models.Model):
    vote = models.ForeignKey(Vote,on_delete=models.PROTECT,related_name='ballots')
    participant = models.ForeignKey(MeetingParticipant,on_delete=models.PROTECT)
    choice = models.CharField(max_length=200)
    request_id = models.UUIDField(default=uuid.uuid4,unique=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['vote','participant'],name='one_ballot_per_elector')]
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError('Stimmabgaben sind unveränderlich.')
        super().save(*args,**kwargs)


class Decision(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    vote = models.OneToOneField(Vote,on_delete=models.PROTECT)
    wording = models.TextField(max_length=100000)
    result = models.JSONField(default=dict,blank=True)
    chair_confirmation = models.CharField(max_length=1000)
    confirmed_by = models.ForeignKey(User,on_delete=models.PROTECT)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    responsible = models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT,related_name='assigned_decisions')
    due_on = models.DateField(null=True,blank=True)
    status = models.CharField(max_length=20,default='open')
    progress = models.TextField(blank=True,max_length=100000)
    version = models.PositiveIntegerField(default=1)


class SessionReturn(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT,related_name='returns')
    base_version = models.PositiveIntegerField()
    bundle = models.JSONField(default=dict)
    digest = models.CharField(max_length=64)
    state = models.CharField(max_length=20,default='pending')
    requested_by = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.PROTECT,related_name='reviewed_session_returns')
    reason = models.CharField(max_length=1000,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Minutes(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    meeting = models.OneToOneField(Meeting,on_delete=models.PROTECT,related_name='minutes')
    kind = models.CharField(max_length=20,default='result',choices=[('result','Ergebnisprotokoll'),('course','Verlaufsprotokoll'),('verbatim','Wortprotokoll')])
    markdown = models.TextField(max_length=200000,blank=True)
    public_markdown = models.TextField(max_length=200000,blank=True)
    state = models.CharField(max_length=20,default='draft')
    version = models.PositiveIntegerField(default=1)
    published_version = models.PositiveIntegerField(null=True,blank=True)
    public_snapshot = models.JSONField(default=dict,blank=True)


class MinutesVersion(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    minutes = models.ForeignKey(Minutes,on_delete=models.PROTECT,related_name='versions')
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    reason = models.CharField(max_length=1000)
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    correction_meeting = models.ForeignKey(Meeting,null=True,blank=True,on_delete=models.PROTECT)
    class Meta:constraints=[models.UniqueConstraint(fields=['minutes','version'],name='unique_minutes_version')]
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Niederschriftsfassungen sind unveränderlich.')
        super().save(*args,**kwargs)


class DecisionUpdate(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    decision = models.ForeignKey(Decision,on_delete=models.PROTECT,related_name='updates')
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():raise ValidationError('Sachstände sind unveränderlich.')
        super().save(*args,**kwargs)


class PersonalNote(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner = models.ForeignKey(User,on_delete=models.PROTECT)
    context = models.ForeignKey(Membership,on_delete=models.PROTECT)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    markdown = models.TextField(max_length=100000,blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['owner','context','meeting'],name='unique_personal_meeting_note')]


class WorkspaceEntry(models.Model):
    owner = models.ForeignKey(User,on_delete=models.CASCADE)
    context = models.ForeignKey(Membership,on_delete=models.CASCADE)
    kind = models.CharField(max_length=20)
    resource_id = models.UUIDField()
    favorite = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(default=timezone.now)
    class Meta:constraints=[models.UniqueConstraint(fields=['owner','context','kind','resource_id'],name='unique_workspace_entry')]


class OfflineReceipt(models.Model):
    id = models.UUIDField(primary_key=True)
    meeting = models.ForeignKey(Meeting,on_delete=models.PROTECT)
    owner = models.ForeignKey(User,on_delete=models.PROTECT)
    context_id = models.UUIDField()
    digest = models.CharField(max_length=64)
    resulting_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class PortalConfiguration(models.Model):
    """Only positive public branding fields are transferred; no executable CSS/HTML."""
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization_id = models.UUIDField(unique=True)
    title = models.CharField(max_length=120,default='Bürgerinformation')
    introduction = models.CharField(max_length=500,blank=True)
    color = models.CharField(max_length=7,default='#245846')
    domains = models.JSONField(default=list,blank=True)
    organizations = models.JSONField(default=list,blank=True)
    frame_origins = models.JSONField(default=list,blank=True)
    version = models.PositiveIntegerField(default=1)
    def clean(self):
        from .portal_configuration import validate
        validate(self)

class PersonProfile(models.Model):
    identity = models.ForeignKey("PersonIdentity",null=True,blank=True,on_delete=models.PROTECT)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    user = models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)
    function = models.CharField(max_length=200,blank=True)
    faction = models.CharField(max_length=200,blank=True)
    starts_on = models.DateField(null=True,blank=True)
    ends_on = models.DateField(null=True,blank=True)
    contact = models.CharField(max_length=300,blank=True)
    photo = models.TextField(blank=True)  # Sanitized small JPEG, no file path/metadata.
    public_fields = models.JSONField(default=list,blank=True)
    published = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

class MailReceipt(models.Model):
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    mailbox = models.CharField(max_length=64)
    uidvalidity = models.PositiveBigIntegerField()
    uid = models.PositiveBigIntegerField()
    category = models.CharField(max_length=30)
    subject = models.CharField(max_length=200,blank=True)
    sender = models.CharField(max_length=200,blank=True)
    preview = models.TextField(max_length=4000,blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True)
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.SET_NULL)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['mailbox','uidvalidity','uid'],name='unique_mail_receipt')]

class MailCursor(models.Model):
    mailbox = models.CharField(primary_key=True,max_length=64)
    uidvalidity = models.PositiveBigIntegerField()
    last_uid = models.PositiveBigIntegerField(default=0)

class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    owner = models.ForeignKey(User,on_delete=models.PROTECT)
    context = models.ForeignKey(Membership,on_delete=models.PROTECT)
    kind = models.CharField(max_length=20)
    rows = models.JSONField(default=list)
    digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True)

class InvitationDispatch(models.Model):
    invitation = models.OneToOneField(Invitation,on_delete=models.CASCADE)
    encrypted_token = models.TextField()
    delivered_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=100,blank=True)

class PersonIdentity(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name = models.CharField(max_length=200)
    user = models.OneToOneField(User,null=True,blank=True,on_delete=models.SET_NULL)
    def __str__(self):return self.name

class SampleBundle(models.Model):
    organization = models.OneToOneField(Organization,on_delete=models.CASCADE)
    parent = models.ForeignKey(Organization,on_delete=models.PROTECT,related_name='sample_bundles')
    record_ids = models.JSONField(default=list)
    membership = models.OneToOneField(Membership,on_delete=models.CASCADE)

class AuthenticationProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    method = models.CharField(max_length=20,default='email')
    secret = models.TextField(blank=True)
    pending_secret = models.TextField(blank=True)
    pending_expires_at = models.DateTimeField(null=True)
    last_counter = models.BigIntegerField(default=-1)
    recovery_hashes = models.JSONField(default=list,blank=True)
    version = models.PositiveIntegerField(default=0)

class Passkey(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    credential_id = models.CharField(max_length=2048,unique=True)
    public_key = models.BinaryField()
    user_handle = models.CharField(max_length=64)
    sign_count = models.PositiveBigIntegerField(default=0)
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

class WebAuthnCeremony(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,null=True,on_delete=models.CASCADE)
    purpose = models.CharField(max_length=20)
    challenge = models.CharField(max_length=100)
    session_digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
    factor_version = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=80,blank=True)

class SystemOperator(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)

class EmergencyAccess(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    operator = models.ForeignKey(User,on_delete=models.PROTECT,related_name='emergency_requests')
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    resource_kind = models.CharField(max_length=20)
    resource_id = models.UUIDField()
    reason = models.CharField(max_length=500)
    expires_at = models.DateTimeField()
    state = models.CharField(max_length=20,default='pending')
    reviewed_by = models.ForeignKey(User,null=True,on_delete=models.SET_NULL,related_name='emergency_reviews')
    membership = models.OneToOneField(Membership,null=True,on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

class RecoveryTicket(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    organization_id = models.UUIDField()
    context_id = models.UUIDField()
    token_digest = models.CharField(max_length=64)
    password_basis = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    state = models.CharField(max_length=20,default='pending')
    reset_factor = models.BooleanField(default=False)
    factor_reset_applied = models.BooleanField(default=False)
    encrypted_token = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)

class TLSPlan(models.Model):
    attempts = models.PositiveIntegerField(default=0)
    apply_requested_at = models.DateTimeField(null=True)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    operator = models.ForeignKey(User,on_delete=models.PROTECT)
    role = models.CharField(max_length=20)
    hostname = models.CharField(max_length=253)
    mode = models.CharField(max_length=20)
    proof = models.CharField(max_length=80)
    expected_ips = models.JSONField(default=list)
    contact = models.EmailField(blank=True)
    encrypted_material = models.TextField(blank=True)
    certificate_info = models.JSONField(default=dict)
    dns_verified_at = models.DateTimeField(null=True)
    state = models.CharField(max_length=20,default='prepared')
    error = models.CharField(max_length=200,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True)
