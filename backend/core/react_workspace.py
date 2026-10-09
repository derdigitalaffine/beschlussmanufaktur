"""Same-origin React workspace; all access decisions remain server-side."""
import json
from functools import wraps
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .member_views import resources
from .models import AuditEvent, Notification, User, WorkspaceEntry
from .permissions import active_context, available_contexts, may_manage_organization


def error(code, message, status=400):
    return JsonResponse({'error': {'code': code, 'message': message}}, status=status)


def endpoint(method):
    def decorate(fn):
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.is_active:
                return error('authentication_required', 'Bitte melden Sie sich erneut an.', 401)
            if request.method != method:
                response = error('method_not_allowed', 'Diese Methode ist nicht erlaubt.', 405)
                response['Allow'] = method
                return response
            try:
                return fn(request, *args, **kwargs)
            except PermissionDenied:
                return error('permission_denied', 'Für diesen Vorgang fehlt die Berechtigung.', 403)
        return wrapped
    return decorate


def context_data(context):
    return {'id': str(context.pk), 'organization_id': str(context.organization_id),
            'organization': context.organization.name,
            'organization_kind': context.organization.get_kind_display(),
            'role': context.role, 'role_label': context.get_role_display(),
            'advanced_enabled': context.organization.advanced_enabled}


def navigation(context):
    def link(label, name):
        return {'label': label, 'url': reverse(name)}

    links = [link('Klassischer Arbeitsplatz', 'home'), link('Anmeldesicherheit', 'security')]
    if not context:
        return links
    links.extend([link('Mein Bereich', 'member_desk'), link('Sitzungen', 'meetings'),
                  link('Vorlagen', 'templates' if settings.SERVER_ROLE == 'internal' else 'replica_documents'),
                  link('Offline-Mappen', 'offline_meetings')])
    if settings.SERVER_ROLE == 'internal':
        links.append(link('Beschlusskontrolle', 'decisions'))
        if may_manage_organization(context):
            links.extend([link('Menschen und Rollen', 'users'),
                          link('Gremien und Stammdaten', 'registry'),
                          link('Portal und Gestaltung', 'portal_configure'),
                          link('Einzelrechte', 'grants'), link('Datenbereitstellung', 'exchange')])
    return links


def bootstrap_data(request):
    context = active_context(request)
    return {'schema': 1, 'csrf_token': get_token(request),
            'username': request.user.first_name or request.user.username,
            'role': settings.SERVER_ROLE,
            'contexts': [context_data(item) for item in available_contexts(request.user)],
            'active_context': context_data(context) if context else None,
            'mode': 'advanced' if context and context.organization.advanced_enabled and request.user.advanced_mode else 'simple',
            'navigation': navigation(context)}


@login_required
@require_GET
def shell(request):
    return render(request, 'react_workspace.html')


@endpoint('GET')
def bootstrap(request):
    return JsonResponse(bootstrap_data(request))


def parse_body(request):
    if request.content_type != 'application/json' or len(request.body) > 8192:
        raise ValueError
    value = json.loads(request.body)
    if not isinstance(value, dict):
        raise ValueError
    return value


def uuid_value(value):
    if not isinstance(value, str):
        raise ValueError
    return UUID(value)


def lock_actor(request):
    request.user = User.objects.select_for_update().get(pk=request.user.pk)
    # Authentication already loaded the session before the user lock. Reload its
    # context here so a concurrent switch cannot authorize a stale mutation.
    if request.session.session_key:
        latest = request.session.__class__(session_key=request.session.session_key).load()
        if 'context_id' in latest:
            request.session['context_id'] = latest['context_id']
        else:
            request.session.pop('context_id', None)
        request.session.modified = False


def bound_context(request, expected):
    try:
        expected_id = uuid_value(expected)
    except (ValueError, TypeError):
        return None, error('invalid_context', 'Bitte wählen Sie einen gültigen Arbeitskontext.')
    if not available_contexts(request.user).filter(pk=expected_id).exists():
        return None, error('context_forbidden', 'Dieser Arbeitskontext ist nicht verfügbar.', 403)
    context = active_context(request)
    if not context or context.pk != expected_id:
        return None, error('context_changed', 'Der Arbeitskontext hat sich geändert. Bitte laden Sie den Arbeitsplatz neu.', 409)
    return context, None


@endpoint('GET')
def resource_list(request):
    context, failure = bound_context(request, request.GET.get('context'))
    if failure is not None:
        return failure
    try:
        page = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '20'))
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError
    except ValueError:
        return error('invalid_pagination', 'Ungültige Seitenauswahl.')
    kind = request.GET.get('kind', 'all')
    if kind not in ('all', 'meeting', 'template'):
        return error('invalid_kind', 'Ungültige Vorgangsart.')
    query = request.GET.get('q', '')
    if len(query) > 100:
        return error('invalid_query', 'Der Suchtext ist zu lang.')
    rows = resources(context, query)
    if kind != 'all':
        rows = [row for row in rows if row['kind'] == kind]
    rows.sort(key=lambda row: (row['title'].casefold(), row['kind'], str(row['id'])))
    total = len(rows)
    rows = rows[(page - 1) * page_size:page * page_size]
    entries = {(entry.kind, entry.resource_id): entry for entry in WorkspaceEntry.objects.filter(owner=request.user, context=context)}
    for row in rows:
        entry = entries.get((row['kind'], row['id']))
        row.update(id=str(row['id']), favorite=bool(entry and entry.favorite),
                   viewed_at=entry.viewed_at.isoformat() if entry else None)
    # Notifications have no context FK. Do not expose titles/links from another role.
    notifications = [{'id': item.pk, 'title': 'Ein Hinweis wartet in Ihrem persönlichen Bereich.',
                      'url': '/mein-bereich/', 'created_at': item.created_at.isoformat()}
                     for item in Notification.objects.filter(user=request.user, read_at__isnull=True).order_by('-created_at')[:20]]
    return JsonResponse({'context': str(context.pk), 'items': rows,
                         'pagination': {'page': page, 'page_size': page_size, 'total': total,
                                        'pages': (total + page_size - 1) // page_size},
                         'notifications': notifications})


@endpoint('POST')
@transaction.atomic
def select_context(request):
    try:
        body = parse_body(request)
        target_id = uuid_value(body['context'])
        if 'expected_context' not in body:
            raise ValueError
        expected = None if body['expected_context'] is None else uuid_value(body['expected_context'])
    except (ValueError, TypeError, KeyError, UnicodeError):
        return error('invalid_request', 'Ungültige Kontextauswahl.')
    lock_actor(request)
    current = active_context(request)
    if (current.pk if current else None) != expected:
        return error('context_changed', 'Der Arbeitskontext hat sich geändert. Bitte laden Sie den Arbeitsplatz neu.', 409)
    target = available_contexts(request.user).filter(pk=target_id).first()
    if not target:
        return error('context_forbidden', 'Dieser Arbeitskontext ist nicht verfügbar.', 403)
    request.session['context_id'] = str(target.pk)
    request.session.save()
    request.session.modified = False
    request.user.last_context = target
    request.user.save(update_fields=['last_context'])
    AuditEvent.objects.create(actor=request.user, action='context.selected', object_id=str(target.pk))
    return JsonResponse(bootstrap_data(request))


@endpoint('POST')
@transaction.atomic
def favorite(request):
    try:
        body = parse_body(request)
        resource_id = uuid_value(body['resource_id'])
        kind = body['kind']
        value = body['favorite']
        if kind not in ('meeting', 'template') or type(value) is not bool:
            raise ValueError
    except (ValueError, TypeError, KeyError, UnicodeError):
        return error('invalid_request', 'Ungültiger Favorit.')
    lock_actor(request)
    context, failure = bound_context(request, body.get('context'))
    if failure is not None:
        return failure
    if not any(row['kind'] == kind and row['id'] == resource_id for row in resources(context)):
        return error('resource_forbidden', 'Dieser Vorgang ist nicht verfügbar.', 403)
    WorkspaceEntry.objects.update_or_create(owner=request.user, context=context, kind=kind,
                                            resource_id=resource_id, defaults={'favorite': value})
    return JsonResponse({'context': str(context.pk), 'resource_id': str(resource_id), 'favorite': value})


@endpoint('POST')
@transaction.atomic
def mode(request):
    try:
        body = parse_body(request)
        selected = body['mode']
        if selected not in ('simple', 'advanced'):
            raise ValueError
    except (ValueError, TypeError, KeyError, UnicodeError):
        return error('invalid_request', 'Ungültige Ansicht.')
    lock_actor(request)
    context, failure = bound_context(request, body.get('context'))
    if failure is not None:
        return failure
    if selected == 'advanced' and not context.organization.advanced_enabled:
        return error('mode_forbidden', 'Die erweiterte Ansicht ist für diesen Kontext nicht freigegeben.', 403)
    request.user.advanced_mode = selected == 'advanced'
    request.user.save(update_fields=['advanced_mode'])
    return JsonResponse({'context': str(context.pk), 'mode': selected})
