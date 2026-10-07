from getpass import getpass

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import AuditEvent, Membership, Organization, User


class Command(BaseCommand):
    help = "Erstes persönliches Konto und Verwaltungsverbund interaktiv einrichten."

    def handle(self, *args, **options):
        if settings.SERVER_ROLE != "internal":
            raise CommandError("Bootstrap ist nur im internen Fachsystem erlaubt.")
        if User.objects.exists():
            raise CommandError("Bereits eingerichtet. Bootstrap legt keine weiteren Konten an.")
        email = input("E-Mail-Adresse: ").strip().lower()
        name = input("Name des Verwaltungsverbunds: ").strip()
        password = getpass("Passwort (mindestens 12 Zeichen): ")
        confirmation = getpass("Passwort wiederholen: ")
        if password != confirmation or not name:
            raise CommandError("Passwörter stimmen nicht überein oder Bezeichnung fehlt.")
        user = User(username=email, email=email)
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        with transaction.atomic():
            # Advisory operator command: one deployment operator runs bootstrap once.
            if User.objects.exists():
                raise CommandError("Bereits eingerichtet.")
            user.set_password(password)
            user.save()
            organization = Organization.objects.create(name=name, kind=Organization.Kind.ADMINISTRATION)
            membership = Membership.objects.create(user=user, organization=organization, role=Membership.Role.ORGANIZATION_ADMIN)
            user.last_context = membership
            user.save(update_fields=["last_context"])
            AuditEvent.objects.create(actor=user, action="installation.bootstrapped", object_id=str(organization.pk))
        self.stdout.write(self.style.SUCCESS("Einrichtung abgeschlossen. Anmeldung mit Passwort und E-Mail-Code."))

