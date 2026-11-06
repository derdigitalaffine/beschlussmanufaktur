"""Regression des einmaligen internen Administrator-Bootstraps.

Der Host-Installer ruft ausschließlich dieses Django-Kommando auf. Die
Sicherheitsgarantien (einmalig, Passwortvalidierung, Organisation, Audit)
müssen daher hier in Integrationstests nachgewiesen werden.
"""
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from core.models import AuditEvent, Membership, Organization, SystemOperator, User


class InitialAdministratorBootstrapTests(TestCase):
    @override_settings(SERVER_ROLE="internal")
    @patch("core.sample_data.create")
    @patch("core.management.commands.bootstrap.getpass", side_effect=[
        "Example-very-strong-password!84", "Example-very-strong-password!84",
    ])
    @patch("builtins.input", side_effect=["admin@example.invalid", "Verwaltungsverbund Test"])
    def test_creates_one_named_administrator_and_organization(self, prompts, passwords, samples):
        output = StringIO()
        call_command("bootstrap", stdout=output)
        self.assertEqual(User.objects.count(), 1)
        account = User.objects.get(email="admin@example.invalid")
        self.assertNotEqual(account.password, "Example-very-strong-password!84")
        self.assertTrue(account.check_password("Example-very-strong-password!84"))
        self.assertEqual(account.username, "admin@example.invalid")
        membership = Membership.objects.get(user=account)
        self.assertEqual(membership.role, Membership.Role.ORGANIZATION_ADMIN)
        self.assertEqual(membership.organization.name, "Verwaltungsverbund Test")
        self.assertEqual(membership.organization.kind, Organization.Kind.ADMINISTRATION)
        self.assertEqual(account.last_context_id, membership.pk)
        self.assertTrue(SystemOperator.objects.filter(user=account).exists())
        self.assertTrue(AuditEvent.objects.filter(actor=account, action="installation.bootstrapped").exists())
        self.assertIn("Einrichtung abgeschlossen", output.getvalue())
        self.assertNotIn("Example-very-strong-password!84", output.getvalue())
        samples.assert_called_once()

    @override_settings(SERVER_ROLE="internal")
    @patch("core.sample_data.create")
    @patch("core.management.commands.bootstrap.getpass", side_effect=[
        "Example-very-strong-password!84", "Example-very-strong-password!84",
    ])
    @patch("builtins.input", side_effect=["admin@example.invalid", "Verbund Eins"])
    def test_second_execution_refused_without_prompt(self, prompts, passwords, samples):
        call_command("bootstrap", stdout=StringIO())
        with patch("builtins.input", side_effect=AssertionError("must not ask again")):
            with patch("core.management.commands.bootstrap.getpass", side_effect=AssertionError("must not read passwords")):
                with self.assertRaisesMessage(CommandError, "Bereits eingerichtet"):
                    call_command("bootstrap", stdout=StringIO())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Membership.objects.count(), 1)

    @override_settings(SERVER_ROLE="public")
    def test_external_role_invalid(self):
        with self.assertRaisesMessage(CommandError, "nur im internen Fachsystem"):
            call_command("bootstrap", stdout=StringIO())

    @override_settings(SERVER_ROLE="protected")
    def test_protected_role_cannot_bootstrap(self):
        with self.assertRaisesMessage(CommandError, "nur im internen Fachsystem"):
            call_command("bootstrap", stdout=StringIO())

    @override_settings(SERVER_ROLE="internal")
    @patch("core.management.commands.bootstrap.getpass", side_effect=["abc123", "abc123"])
    @patch("builtins.input", side_effect=["admin@example.invalid", "Verbund"])
    def test_weak_password_leaves_database_empty(self, prompts, passwords):
        with self.assertRaises(CommandError):
            call_command("bootstrap", stdout=StringIO())
        self.assertFalse(User.objects.exists())
        self.assertFalse(Organization.objects.exists())

    @override_settings(SERVER_ROLE="internal")
    @patch("core.management.commands.bootstrap.getpass", side_effect=["one-password", "different-password"])
    @patch("builtins.input", side_effect=["admin@example.invalid", "Verbund"])
    def test_password_confirmation_does_not_create_user(self, prompts, passwords):
        with self.assertRaisesMessage(CommandError, "Passwörter stimmen nicht"):
            call_command("bootstrap", stdout=StringIO())
        self.assertFalse(User.objects.exists())
        self.assertFalse(Organization.objects.exists())
