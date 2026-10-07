import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from .invitations import accept_invitation, create_invitation, invitation_for_token
from .models import AuditEvent, Invitation, Membership, Organization, User
from .network import client_address


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", email="admin@example.invalid", password="A-valid-password-2026")
        self.organization = Organization.objects.create(name="Verwaltungsverbund", kind="administration")
        self.context = Membership.objects.create(user=self.admin, organization=self.organization, role="organization_admin")
        self.other_organization = Organization.objects.create(name="Andere Kommune", kind="municipality")
        self.activate(self.admin, self.context)

    def activate(self, user, context):
        self.client.force_login(user)
        session = self.client.session
        session["context_id"] = str(context.pk)
        session.save()

    def invite(self, email="new@example.invalid", role="author"):
        response = self.client.post("/benutzer/", {"email": email, "role": role})
        self.assertEqual(response.status_code, 302)
        token = re.search(r"Einladungscode: ([A-Za-z0-9_-]{43})", mail.outbox[-1].body).group(1)
        return Invitation.objects.latest("created_at"), token

    def open_invitation(self, token, client=None):
        client = client or self.client
        response = client.post("/einladung/", {"token": token})
        self.assertRedirects(response, "/einladung/annehmen/")
        return client

    def account_data(self):
        return {"first_name": "Anna", "last_name": "Muster", "password": "A-valid-password-2026", "password_confirm": "A-valid-password-2026"}

    def test_invitation_does_not_create_account_or_grant_access(self):
        invitation, token = self.invite()
        self.assertFalse(User.objects.filter(email=invitation.email).exists())
        self.assertEqual(Membership.objects.count(), 1)
        self.assertNotIn(token, invitation.token_digest)
        self.assertNotIn(token, str(list(AuditEvent.objects.values("metadata"))))

    @override_settings(APPLICATION_URL="https://configured.example")
    def test_email_uses_configured_origin_and_fragment_not_request_host(self):
        invitation, token = self.invite()
        self.assertIn(f"https://configured.example/einladung/#{token}", mail.outbox[0].body)
        self.assertNotIn(f"?token={token}", mail.outbox[0].body)

    def test_anonymous_new_user_sets_own_password_then_needs_mfa_login(self):
        invitation, token = self.invite()
        anonymous = self.open_invitation(token, Client())
        response = anonymous.post("/einladung/annehmen/", self.account_data())
        self.assertRedirects(response, "/anmelden/")
        self.assertNotIn("_auth_user_id", anonymous.session)
        user = User.objects.get(email=invitation.email)
        self.assertTrue(user.check_password(self.account_data()["password"]))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(Membership.objects.filter(user=user, organization=self.organization, role="author").exists())
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)

    def test_weak_password_rejected_without_consuming_invitation(self):
        invitation, token = self.invite()
        anonymous = self.open_invitation(token, Client())
        data = self.account_data() | {"password": "short", "password_confirm": "short"}
        self.assertEqual(anonymous.post("/einladung/annehmen/", data).status_code, 200)
        self.assertFalse(User.objects.filter(email=invitation.email).exists())
        invitation.refresh_from_db()
        self.assertIsNone(invitation.accepted_at)

    def test_password_confirmation_required(self):
        invitation, token = self.invite()
        anonymous = self.open_invitation(token, Client())
        response = anonymous.post("/einladung/annehmen/", self.account_data() | {"password_confirm": "Different-password-2026"})
        self.assertContains(response, "Passwörter stimmen nicht überein")
        self.assertFalse(User.objects.filter(email=invitation.email).exists())

    def test_existing_account_must_authenticate_before_role_acceptance(self):
        user = User.objects.create_user("existing", email="existing@example.invalid", password="Original-password-2026")
        invitation, token = self.invite(user.email)
        anonymous = self.open_invitation(token, Client())
        self.assertContains(anonymous.get("/einladung/annehmen/"), "Bestehendes Konto verwenden")
        self.assertEqual(anonymous.post("/einladung/annehmen/", self.account_data()).status_code, 403)
        self.assertFalse(Membership.objects.filter(user=user).exists())

    def test_existing_account_accepts_without_password_or_profile_change(self):
        user = User.objects.create_user("existing", email="existing@example.invalid", password="Original-password-2026", first_name="Original")
        invitation, token = self.invite(user.email)
        client = self.open_invitation(token, Client())
        client.force_login(user)
        self.assertRedirects(client.post("/einladung/annehmen/", self.account_data()), "/")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Original-password-2026"))
        self.assertEqual(user.first_name, "Original")

    def test_other_authenticated_account_cannot_accept(self):
        invitation, token = self.invite()
        self.open_invitation(token)
        self.assertContains(self.client.get("/einladung/annehmen/"), "Anderes Konto angemeldet")
        self.assertEqual(self.client.post("/einladung/annehmen/", self.account_data()).status_code, 403)

    def test_invitation_survives_existing_users_email_mfa_login(self):
        user = User.objects.create_user("existing", email="existing@example.invalid", password="Original-password-2026")
        invitation, token = self.invite(user.email)
        client = self.open_invitation(token, Client())
        client.post("/anmelden/", {"email": user.email, "password": "Original-password-2026"})
        code = re.search(r"\b[0-9]{6}\b", mail.outbox[-1].body).group()
        self.assertRedirects(client.post("/anmelden/code/", {"code": code}), "/einladung/annehmen/")
        self.assertEqual(client.session["pending_invitation"], str(invitation.pk))

    def test_single_use_and_replay_rejected(self):
        invitation, token = self.invite()
        anonymous = self.open_invitation(token, Client())
        anonymous.post("/einladung/annehmen/", self.account_data())
        self.assertIsNone(invitation_for_token(token))
        self.assertContains(Client().post("/einladung/", {"token": token}), "Einladung ungültig")
        self.assertEqual(Membership.objects.filter(organization=self.organization, role="author").count(), 1)

    def test_expired_invitation_rejected(self):
        invitation, token = self.invite()
        invitation.expires_at = timezone.now()-timedelta(seconds=1)
        invitation.save()
        self.assertIsNone(invitation_for_token(token))
        self.assertContains(Client().post("/einladung/", {"token": token}), "Einladung ungültig")

    def test_revoked_invitation_is_rechecked_after_token_exchange(self):
        invitation, token = self.invite()
        anonymous = self.open_invitation(token, Client())
        response = self.client.post(f"/benutzer/einladungen/{invitation.pk}/zurueckziehen/", {"reason": "Fehleinladung"})
        self.assertRedirects(response, "/benutzer/")
        self.assertRedirects(anonymous.post("/einladung/annehmen/", self.account_data()), "/einladung/")
        self.assertFalse(User.objects.filter(email=invitation.email).exists())

    def test_inviters_removed_authority_prevents_acceptance(self):
        invitation, token = self.invite()
        self.context.revoked_at = timezone.now()
        self.context.save()
        self.assertIsNone(invitation_for_token(token))
        with self.assertRaises(ValidationError):
            accept_invitation(invitation.pk, AnonymousUser(), self.account_data())
        self.assertFalse(User.objects.filter(email=invitation.email).exists())

    def test_future_role_is_not_immediately_available(self):
        invitation, token = self.invite()
        invitation.starts_at = timezone.now()+timedelta(days=2)
        invitation.save()
        anonymous = self.open_invitation(token, Client())
        anonymous.post("/einladung/annehmen/", self.account_data())
        user = User.objects.get(email=invitation.email)
        from .permissions import available_contexts
        self.assertFalse(available_contexts(user).exists())

    def test_expired_assignment_cannot_be_created_by_old_invitation(self):
        invitation, token = self.invite()
        invitation.starts_at = timezone.now()-timedelta(days=2)
        invitation.ends_at = timezone.now()-timedelta(days=1)
        invitation.save()
        self.assertIsNone(invitation_for_token(token))

    def test_duplicate_pending_invitation_rejected(self):
        self.invite()
        response = self.client.post("/benutzer/", {"email": "NEW@example.invalid", "role": "author"})
        self.assertContains(response, "bereits eine offene Einladung")
        self.assertEqual(Invitation.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    @patch("core.invitations.send_mail", side_effect=RuntimeError("mail unavailable"))
    def test_failed_email_rolls_back_invitation_and_audit(self, send):
        response = self.client.post("/benutzer/", {"email": "new@example.invalid", "role": "author"})
        self.assertContains(response, "konnte nicht versendet")
        self.assertFalse(Invitation.objects.exists())
        self.assertFalse(AuditEvent.objects.filter(action="invitation.sent").exists())

    def test_empty_submission_does_not_create_invitation(self):
        self.assertEqual(self.client.post("/benutzer/", {}).status_code, 200)
        self.assertFalse(Invitation.objects.exists())

    def test_no_free_registration_without_invitation(self):
        anonymous = Client()
        self.assertRedirects(anonymous.post("/einladung/annehmen/", self.account_data()), "/einladung/")
        self.assertEqual(User.objects.count(), 1)

    def test_admin_list_is_scoped_and_search_does_not_enumerate_other_accounts(self):
        stranger = User.objects.create_user("stranger", email="stranger@example.invalid")
        Membership.objects.create(user=stranger, organization=self.other_organization, role="author")
        self.assertNotContains(self.client.get("/benutzer/"), stranger.email)
        self.assertNotContains(self.client.get("/benutzer/?q=stranger"), stranger.email)

    def test_other_organizations_role_is_not_editable_by_id(self):
        stranger = User.objects.create_user("stranger", email="stranger@example.invalid")
        foreign = Membership.objects.create(user=stranger, organization=self.other_organization, role="author")
        for suffix in ["", "entziehen/"]:
            self.assertEqual(self.client.post(f"/benutzer/rollen/{foreign.pk}/{suffix}", {"role": "organization_admin", "reason": "attack"}).status_code, 404)

    def test_last_admin_cannot_be_revoked_or_demoted(self):
        response = self.client.post(f"/benutzer/rollen/{self.context.pk}/entziehen/", {"reason": "Test", "version": 1})
        self.assertContains(response, "letzte aktive Organisationsverwaltung")
        response = self.client.post(f"/benutzer/rollen/{self.context.pk}/", {"role": "author", "reason": "Test", "version": 1})
        self.assertContains(response, "letzte aktive Organisationsverwaltung")
        self.context.refresh_from_db()
        self.assertIsNone(self.context.revoked_at)
        self.assertEqual(self.context.role, "organization_admin")

    def test_role_change_and_revocation_are_audited_and_org_scoped(self):
        user = User.objects.create_user("member", email="member@example.invalid")
        local = Membership.objects.create(user=user, organization=self.organization, role="member")
        other = Membership.objects.create(user=user, organization=self.other_organization, role="member")
        response = self.client.post(f"/benutzer/rollen/{local.pk}/", {"role": "author", "reason": "Neue Aufgabe", "version": 1})
        self.assertRedirects(response, "/benutzer/")
        self.assertEqual(AuditEvent.objects.get(action="membership.changed").metadata["before"]["role"], "member")
        response = self.client.post(f"/benutzer/rollen/{local.pk}/entziehen/", {"reason": "Aufgabe beendet", "version": 2})
        self.assertRedirects(response, "/benutzer/")
        local.refresh_from_db(); other.refresh_from_db(); user.refresh_from_db()
        self.assertIsNotNone(local.revoked_at)
        self.assertIsNone(other.revoked_at)
        self.assertTrue(user.is_active)

    def test_revoked_role_cannot_be_reactivated(self):
        user = User.objects.create_user("member", email="member@example.invalid")
        member = Membership.objects.create(user=user, organization=self.organization, role="member", revoked_at=timezone.now())
        response = self.client.post(f"/benutzer/rollen/{member.pk}/", {"role": "author", "reason": "Test", "version": 1})
        self.assertContains(response, "kann nicht reaktiviert")

    def test_regular_member_cannot_invite_or_manage(self):
        user = User.objects.create_user("member", email="member@example.invalid")
        member = Membership.objects.create(user=user, organization=self.organization, role="member")
        self.activate(user, member)
        self.assertEqual(self.client.get("/benutzer/").status_code, 403)
        self.assertEqual(self.client.post("/benutzer/", {"email": "new@example.invalid", "role": "organization_admin"}).status_code, 403)

    def test_end_date_must_follow_start(self):
        response = self.client.post("/benutzer/", {"email": "new@example.invalid", "role": "author", "starts_at": "2030-01-02T10:00", "ends_at": "2030-01-01T10:00"})
        self.assertContains(response, "Ende muss nach dem Beginn")
        self.assertFalse(Invitation.objects.exists())

    def test_get_requests_cannot_mutate_access(self):
        self.client.get(f"/benutzer/rollen/{self.context.pk}/entziehen/")
        self.context.refresh_from_db()
        self.assertIsNone(self.context.revoked_at)
        self.assertFalse(Invitation.objects.exists())

    def test_csrf_required_for_invitation_exchange_and_admin_action(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/einladung/", {"token": "a"*43}).status_code, 403)
        client.force_login(self.admin)
        self.assertEqual(client.post("/benutzer/", {"email": "new@example.invalid", "role": "author"}).status_code, 403)

    def test_stale_role_edit_and_revocation_rejected(self):
        user = User.objects.create_user("member", email="member@example.invalid")
        member = Membership.objects.create(user=user, organization=self.organization, role="member")
        self.client.post(f"/benutzer/rollen/{member.pk}/", {"role": "author", "reason": "Neue Aufgabe", "version": 1})
        response = self.client.post(f"/benutzer/rollen/{member.pk}/", {"role": "organization_admin", "reason": "Alter Stand", "version": 1})
        self.assertContains(response, "zwischenzeitlich geändert")
        response = self.client.post(f"/benutzer/rollen/{member.pk}/entziehen/", {"reason": "Alter Stand", "version": 1})
        self.assertContains(response, "zwischenzeitlich geändert")
        member.refresh_from_db()
        self.assertEqual(member.role, "author")
        self.assertIsNone(member.revoked_at)

    def test_member_expiry_is_applied_without_a_scheduled_worker(self):
        user = User.objects.create_user("member", email="member@example.invalid")
        member = Membership.objects.create(user=user, organization=self.organization, role="author", starts_at=timezone.now()-timedelta(days=2), ends_at=timezone.now()-timedelta(days=1))
        self.activate(user, member)
        self.assertContains(self.client.get("/"), "keine gültige Organisationsrolle")

    def test_changed_role_invalidates_existing_admin_session(self):
        user = User.objects.create_user("second_admin", email="second@example.invalid")
        member = Membership.objects.create(user=user, organization=self.organization, role="organization_admin")
        other_client = Client()
        other_client.force_login(user)
        session = other_client.session
        session["context_id"] = str(member.pk)
        session.save()
        self.client.post(f"/benutzer/rollen/{member.pk}/", {"role": "author", "reason": "Neue Aufgabe", "version": 1})
        self.assertEqual(other_client.get("/benutzer/").status_code, 403)

    @override_settings(TRUST_PROXY_HEADERS=False)
    def test_forwarded_address_untrusted_by_default(self):
        request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.5")
        self.assertEqual(client_address(request), "127.0.0.1")

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_private_proxy_can_apply_rate_limits_per_client(self):
        request = RequestFactory().get("/", REMOTE_ADDR="172.20.0.5", HTTP_X_FORWARDED_FOR="198.51.100.5")
        self.assertEqual(client_address(request), "198.51.100.5")

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_invalid_forwarded_address_falls_back_to_peer(self):
        request = RequestFactory().get("/", REMOTE_ADDR="172.20.0.5", HTTP_X_FORWARDED_FOR="invalid")
        self.assertEqual(client_address(request), "172.20.0.5")
