"""Independent regression tests for the React workspace's server-side boundary."""
import json
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone

from .models import Membership, Organization, Template, TemplateKind, User, WorkspaceEntry

API = '/api/v1/arbeitsplatz/'


class ReactWorkspaceSecurityTests(TestCase):
    def setUp(self):
        if settings.SERVER_ROLE != 'internal':
            self.skipTest('Run isolated server-role tests for external route boundaries.')
        self.user = User.objects.create_user('react-person', email='react@example.invalid', password='Safe-test-password-2026')
        self.a = Organization.objects.create(name='Körperschaft A', kind='association')
        self.b = Organization.objects.create(name='Körperschaft B', kind='municipality')
        self.clerk = Membership.objects.create(user=self.user, organization=self.a, role='clerk')
        self.member = Membership.objects.create(user=self.user, organization=self.a, role='member')
        self.other = Membership.objects.create(user=self.user, organization=self.b, role='clerk')
        author = User.objects.create_user('other-author', email='author@example.invalid')
        self.private = Template.objects.create(organization=self.a, kind=TemplateKind.objects.create(organization=self.a, name='Beschluss'), author=author, subject='GEHEIM-A-ONLY', markdown='Private Akte')
        self.foreign = Template.objects.create(organization=self.b, kind=TemplateKind.objects.create(organization=self.b, name='Beschluss'), author=author, subject='GEHEIM-B-ONLY', markdown='Andere Akte')
        self.client.force_login(self.user)
        self.select(self.clerk)

    def select(self, membership):
        session = self.client.session
        session['context_id'] = str(membership.pk)
        session.save()

    def post(self, path, payload, client=None, **extra):
        return (client or self.client).post(API + path, data=json.dumps(payload), content_type='application/json', **extra)

    def resources(self, membership, **params):
        return self.client.get(API + 'ressourcen/', {'context': str(membership.pk), **params})

    def test_unauthenticated_api_is_json_401_without_html_redirect(self):
        response = Client().get(API)
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())
        self.assertNotIn('Location', response)

    def test_password_step_alone_does_not_authenticate_api(self):
        client = Client()
        response = client.post('/anmelden/', {'email': self.user.email, 'password': 'Safe-test-password-2026'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/anmelden/code/')
        self.assertEqual(client.get(API).status_code, 401)

    def test_bootstrap_uses_explicit_context_and_never_unions_roles(self):
        response = self.client.get(API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['active_context']['id'], str(self.clerk.pk))
        self.assertTrue(response.json()['csrf_token'])
        self.assertContains(self.resources(self.clerk), 'GEHEIM-A-ONLY')
        self.assertNotContains(self.resources(self.clerk), 'GEHEIM-B-ONLY')
        self.select(self.member)
        data = self.resources(self.member).json()
        self.assertEqual(data['items'], [])
        self.assertEqual(data['pagination']['total'], 0)
        self.assertNotIn('GEHEIM-A-ONLY', json.dumps(data))

    def test_missing_context_does_not_automatically_select_available_role(self):
        session = self.client.session
        session.pop('context_id', None)
        session.save()
        response = self.client.get(API)
        self.assertIsNone(response.json()['active_context'])
        self.assertEqual(self.client.get(API + 'ressourcen/').status_code, 400)

    def test_stale_context_read_and_mutation_return_conflict_without_data(self):
        for response in [self.resources(self.other), self.post('favorit/', {'context': str(self.other.pk), 'kind': 'template', 'resource_id': str(self.foreign.pk), 'favorite': True}), self.post('modus/', {'context': str(self.other.pk), 'mode': 'advanced'})]:
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()['error']['code'], 'context_changed')
            self.assertNotIn('GEHEIM', response.content.decode())
        self.assertFalse(WorkspaceEntry.objects.exists())
        self.user.refresh_from_db()
        self.assertFalse(self.user.advanced_mode)

    def test_context_compare_and_swap_prevents_stale_tab_overriding_new_choice(self):
        response = self.post('kontext/', {'context': str(self.other.pk), 'expected_context': str(self.clerk.pk)})
        self.assertEqual(response.status_code, 200)
        response = self.post('kontext/', {'context': str(self.member.pk), 'expected_context': str(self.clerk.pk)})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(API).json()['active_context']['id'], str(self.other.pk))

    def test_revoked_and_expired_contexts_are_not_available(self):
        self.clerk.revoked_at = timezone.now()
        self.clerk.save(update_fields=['revoked_at'])
        response = self.resources(self.clerk)
        self.assertEqual(response.status_code, 403)
        self.other.starts_at = timezone.now() - timedelta(days=2)
        self.other.ends_at = timezone.now() - timedelta(days=1)
        self.other.save(update_fields=['starts_at', 'ends_at'])
        self.assertEqual(self.post('kontext/', {'context': str(self.other.pk), 'expected_context': None}).status_code, 403)
        available = [item['id'] for item in self.client.get(API).json()['contexts']]
        self.assertNotIn(str(self.clerk.pk), available)
        self.assertNotIn(str(self.other.pk), available)

    def test_other_users_context_and_unreadable_resource_cannot_be_favorited(self):
        stranger = User.objects.create_user('stranger', email='stranger@example.invalid')
        alien = Membership.objects.create(user=stranger, organization=self.a, role='clerk')
        self.assertEqual(self.post('kontext/', {'context': str(alien.pk), 'expected_context': str(self.clerk.pk)}).status_code, 403)
        self.assertEqual(self.post('favorit/', {'context': str(self.clerk.pk), 'kind': 'template', 'resource_id': str(self.foreign.pk), 'favorite': True}).status_code, 403)
        self.assertFalse(WorkspaceEntry.objects.exists())

    def test_superuser_without_fachcontext_has_no_private_resources(self):
        operator = User.objects.create_superuser('operator', 'operator@example.invalid', 'Safe-test-password-2026')
        self.client.force_login(operator)
        self.assertEqual(self.client.get(API).json()['contexts'], [])
        self.assertEqual(self.resources(self.clerk).status_code, 403)
        self.assertNotIn('GEHEIM', self.client.get(API).content.decode())

    def test_real_csrf_enforcement_rejects_missing_invalid_and_foreign_origin(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        session = client.session
        session['context_id'] = str(self.clerk.pk)
        session.save()
        token = client.get(API).json()['csrf_token']
        payload = {'context': str(self.clerk.pk), 'mode': 'advanced'}
        for headers in [{}, {'HTTP_X_CSRFTOKEN': 'invalid'}, {'HTTP_X_CSRFTOKEN': token, 'HTTP_ORIGIN': 'https://evil.example.invalid'}]:
            self.assertEqual(self.post('modus/', payload, client=client, **headers).status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.advanced_mode)
        self.assertEqual(self.post('modus/', payload, client=client, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_input_validation_and_favorite_idempotence(self):
        self.assertEqual(self.resources(self.clerk, kind='everything').status_code, 400)
        self.assertEqual(self.resources(self.clerk, page='no').status_code, 400)
        self.assertEqual(self.post('favorit/', {'context': str(self.clerk.pk), 'kind': 'template', 'resource_id': str(uuid4()), 'favorite': 'false'}).status_code, 400)
        payload = {'context': str(self.clerk.pk), 'kind': 'template', 'resource_id': str(self.private.pk), 'favorite': True}
        for _ in range(2):
            self.assertEqual(self.post('favorit/', payload).status_code, 200)
        self.assertEqual(WorkspaceEntry.objects.filter(owner=self.user, context=self.clerk, favorite=True).count(), 1)
        payload['favorite'] = False
        self.assertEqual(self.post('favorit/', payload).status_code, 200)
        self.assertFalse(WorkspaceEntry.objects.filter(favorite=True).exists())

    def test_disabled_advanced_mode_cannot_be_enabled_by_api(self):
        self.a.advanced_enabled = False
        self.a.save(update_fields=['advanced_enabled'])
        response = self.post('modus/', {'context': str(self.clerk.pk), 'mode': 'advanced'})
        self.assertIn(response.status_code, [400, 403])
        self.user.refresh_from_db()
        self.assertFalse(self.user.advanced_mode)


class ReactServerBoundaryTests(TestCase):
    def test_public_server_has_no_react_private_shell_or_workspace_api(self):
        if settings.SERVER_ROLE != 'public':
            self.skipTest('Separate public-role process required')
        for path in ['/arbeitsplatz/', API, API + 'ressourcen/', API + 'kontext/', API + 'favorit/', API + 'modus/']:
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.post(path, {}, content_type='application/json').status_code, 404)

    def test_protected_role_requires_fresh_rights_projection(self):
        if settings.SERVER_ROLE != 'protected':
            self.skipTest('Separate protected-role process required')
        user = User.objects.create_user('protected-test', email='protected@example.invalid')
        organization = Organization.objects.create(name='Protected', kind='association')
        context = Membership.objects.create(user=user, organization=organization, role='clerk')
        self.client.force_login(user)
        session = self.client.session
        session['context_id'] = str(context.pk)
        session.save()
        self.assertEqual(self.client.get(API).json()['contexts'], [])
        response = self.client.get(API + 'ressourcen/', {'context': str(context.pk)})
        self.assertEqual(response.status_code, 403)
        for path in ['/benutzer/', '/verwaltung/import/', '/stammdaten/']:
            self.assertEqual(self.client.get(path).status_code, 404)
