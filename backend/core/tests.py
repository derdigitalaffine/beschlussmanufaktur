import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from .models import EmailChallenge, Membership, Organization, User
from .permissions import available_contexts
from .services import consume_rate_limit, verify_challenge


class FoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", email="anna@example.invalid", password="secure-password-123")
        self.organization = Organization.objects.create(name="Verwaltungsverbund", kind="administration")
        self.membership = Membership.objects.create(user=self.user, organization=self.organization, role="organization_admin")

    def activate(self, user=None, membership=None):
        self.client.force_login(user or self.user)
        session = self.client.session
        session["context_id"] = str((membership or self.membership).pk)
        session.save()

    def test_password_alone_does_not_authenticate(self):
        response = self.client.post("/anmelden/", {"email": self.user.email, "password": "secure-password-123"})
        self.assertRedirects(response, "/anmelden/code/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r"\b[0-9]{6}\b", mail.outbox[0].body).group()
        self.assertNotIn(code, EmailChallenge.objects.get().code_hash)
        response = self.client.post("/anmelden/code/", {"code": code})
        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_code_is_single_use(self):
        challenge = EmailChallenge.objects.create(user=self.user, code_hash=make_password("123456"), expires_at=timezone.now()+timedelta(minutes=5))
        self.assertEqual(verify_challenge(challenge.pk, "123456"), self.user)
        self.assertIsNone(verify_challenge(challenge.pk, "123456"))

    def test_expired_code_and_inactive_user_rejected(self):
        challenge = EmailChallenge.objects.create(user=self.user, code_hash=make_password("123456"), expires_at=timezone.now()-timedelta(seconds=1))
        self.assertIsNone(verify_challenge(challenge.pk, "123456"))
        challenge.expires_at = timezone.now()+timedelta(minutes=5)
        challenge.save()
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(verify_challenge(challenge.pk, "123456"))

    def test_five_wrong_attempts_exhaust_challenge(self):
        challenge = EmailChallenge.objects.create(user=self.user, code_hash=make_password("123456"), expires_at=timezone.now()+timedelta(minutes=5))
        for _ in range(5):
            self.assertIsNone(verify_challenge(challenge.pk, "000000"))
        self.assertIsNone(verify_challenge(challenge.pk, "123456"))

    @patch("core.services.send_mail", side_effect=RuntimeError("SMTP unavailable"))
    def test_email_failure_cannot_leave_usable_challenge(self, send):
        response = self.client.post("/anmelden/", {"email": self.user.email, "password": "secure-password-123"})
        self.assertContains(response, "Anmeldung derzeit nicht möglich")
        self.assertEqual(EmailChallenge.objects.count(), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_rate_limit_is_bounded(self):
        self.assertTrue(consume_rate_limit("account:test", maximum=2))
        self.assertTrue(consume_rate_limit("account:test", maximum=2))
        self.assertFalse(consume_rate_limit("account:test", maximum=2))

    def test_other_persons_context_cannot_be_selected(self):
        other = User.objects.create_user("bert", email="bert@example.invalid")
        foreign = Membership.objects.create(user=other, organization=self.organization, role="organization_admin")
        self.activate()
        response = self.client.post("/kontext/", {"context": foreign.pk})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session["context_id"], str(self.membership.pk))

    def test_expired_revoked_and_future_contexts_excluded(self):
        self.membership.ends_at = timezone.now()+timedelta(hours=1)
        self.membership.save()
        future = Membership.objects.create(user=self.user, organization=self.organization, role="member", starts_at=timezone.now()+timedelta(days=1))
        self.assertEqual(list(available_contexts(self.user)), [self.membership])
        self.membership.revoked_at = timezone.now()
        self.membership.save()
        self.assertFalse(available_contexts(self.user).exists())
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/kontext/", {"context": future.pk}).status_code, 403)

    def test_revocation_applies_to_existing_session(self):
        self.activate()
        self.membership.revoked_at = timezone.now()
        self.membership.save()
        self.assertEqual(self.client.post("/organisationen/neu/", {"name": "Fremd", "kind": "municipality"}).status_code, 403)
        self.assertEqual(Organization.objects.count(), 1)

    def test_technical_admin_has_no_implicit_fach_access(self):
        admin = User.objects.create_superuser("root", "root@example.invalid", "secure-password-123")
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/organisationen/neu/").status_code, 403)
        self.assertContains(self.client.get("/"), "keine gültige Organisationsrolle")

    def test_member_cannot_create_organization(self):
        self.membership.role = "member"
        self.membership.save()
        self.activate()
        self.assertEqual(self.client.post("/organisationen/neu/", {"name": "Neu", "kind": "municipality"}).status_code, 403)

    def test_child_creation_assigns_explicit_access(self):
        self.activate()
        response = self.client.post("/organisationen/neu/", {"name": "Ortsgemeinde", "kind": "municipality"})
        self.assertRedirects(response, "/")
        child = Organization.objects.get(name="Ortsgemeinde")
        self.assertEqual(child.primary_parent, self.organization)
        self.assertTrue(Membership.objects.filter(user=self.user, organization=child, role="organization_admin").exists())

    def test_no_implicit_child_access(self):
        Organization.objects.create(name="Unsichtbare Gemeinde", kind="municipality", primary_parent=self.organization)
        self.activate()
        self.assertNotContains(self.client.get("/"), "Unsichtbare Gemeinde")

    def test_context_is_remembered_and_shown(self):
        self.activate()
        self.client.post("/kontext/", {"context": self.membership.pk})
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_context, self.membership)
        self.assertContains(self.client.get("/"), "Aktiver Arbeitskontext")
        self.assertContains(self.client.get("/"), self.organization.name)

    def test_primary_tree_rejects_cycle(self):
        child = Organization.objects.create(name="Kind", kind="municipality", primary_parent=self.organization)
        self.organization.primary_parent = child
        with self.assertRaises(ValidationError):
            self.organization.full_clean()

    def test_email_is_case_insensitive_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("duplicate", email="ANNA@example.invalid")

    def test_csrf_is_enforced_for_context_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/kontext/", {"context": self.membership.pk}).status_code, 403)

    def test_logout_cannot_be_triggered_by_get(self):
        self.activate()
        self.assertEqual(self.client.get("/abmelden/").status_code, 405)

    def test_security_headers_and_private_caching(self):
        self.activate()
        response = self.client.get("/")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")

    def test_health_endpoints(self):
        self.assertEqual(self.client.get("/health/live/").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/health/ready/").status_code, 200)

