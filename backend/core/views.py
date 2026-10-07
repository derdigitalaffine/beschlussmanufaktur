from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.db.utils import DatabaseError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import CodeForm, OrganizationForm, SignInForm
from .models import AuditEvent, Membership, User
from .network import client_address
from .permissions import active_context, available_contexts, may_manage_organization
from .services import consume_rate_limit, issue_challenge, verify_challenge


@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def public_home(request):
    return render(request, "public.html")


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignInForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        ip_allowed = consume_rate_limit("ip:" + client_address(request), maximum=30)
        account_allowed = consume_rate_limit("account:" + email)
        if not ip_allowed or not account_allowed:
            form.add_error(None, "Zu viele Versuche. Bitte versuchen Sie es später erneut.")
        else:
            candidate = User.objects.filter(email=email).first()
            user = authenticate(request, username=candidate.username if candidate else email, password=form.cleaned_data["password"])
            if user and candidate and user.pk == candidate.pk:
                try:
                    challenge = issue_challenge(user)
                except Exception:
                    form.add_error(None, "Anmeldung derzeit nicht möglich. Bitte versuchen Sie es später erneut.")
                else:
                    request.session.cycle_key()
                    request.session["pending_challenge"] = str(challenge.pk)
                    return redirect("verify_code")
            else:
                form.add_error(None, "Anmeldung nicht möglich. Bitte prüfen Sie Ihre Zugangsdaten.")
    return render(request, "auth.html", {"form": form, "title": "Willkommen zurück", "description": "Melden Sie sich mit Ihrem persönlichen Konto an.", "button": "Anmeldecode anfordern"})


def verify_code(request):
    challenge_id = request.session.get("pending_challenge")
    if not challenge_id:
        return redirect("sign_in")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = verify_challenge(challenge_id, form.cleaned_data["code"])
        if user:
            request.session.pop("pending_challenge", None)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if settings.SERVER_ROLE == "internal" and request.session.get("pending_invitation"):
                return redirect("accept_invitation")
            return redirect("home")
        form.add_error(None, "Code ungültig, abgelaufen oder zu oft versucht. Fordern Sie bei Bedarf einen neuen Code an.")
    return render(request, "auth.html", {"form": form, "title": "Anmeldung bestätigen", "description": "Geben Sie den sechsstelligen Code aus Ihrer E-Mail ein.", "button": "Sicher anmelden", "code_step": True})


@require_POST
def sign_out(request):
    logout(request)
    return redirect("sign_in")


@login_required
def dashboard(request):
    contexts = available_contexts(request.user)
    context = active_context(request)
    return render(request, "dashboard.html", {
        "contexts": contexts, "context": context,
        "can_manage": settings.SERVER_ROLE == "internal" and may_manage_organization(context),
    })


@login_required
@require_POST
def select_context(request):
    try:
        context_id = UUID(request.POST.get("context", ""))
    except (ValueError, TypeError):
        return HttpResponseForbidden("Ungültiger Arbeitskontext.")
    context = available_contexts(request.user).filter(pk=context_id).first()
    if not context:
        return HttpResponseForbidden("Dieser Arbeitskontext ist nicht verfügbar.")
    request.session["context_id"] = str(context.pk)
    request.user.last_context = context
    request.user.save(update_fields=["last_context"])
    AuditEvent.objects.create(actor=request.user, action="context.selected", object_id=str(context.pk))
    return redirect("home")


@login_required
def create_organization(request):
    context = active_context(request)
    if not may_manage_organization(context):
        return HttpResponseForbidden("Für diese Aktion fehlt die Organisationsberechtigung.")
    form = OrganizationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            organization = form.save(commit=False)
            organization.primary_parent = context.organization
            organization.full_clean()
            organization.save()
            membership = Membership.objects.create(user=request.user, organization=organization, role=Membership.Role.ORGANIZATION_ADMIN)
            AuditEvent.objects.create(actor=request.user, action="organization.created", object_id=str(organization.pk), metadata={"explicit_assignment": str(membership.pk)})
        messages.success(request, "Organisation angelegt. Ihr Verwaltungszugriff wurde ausdrücklich zugewiesen.")
        return redirect("home")
    return render(request, "organization_form.html", {"form": form, "context": context})
