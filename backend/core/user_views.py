from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import InvitationAccountForm, InvitationCodeForm, InvitationForm, MembershipChangeForm, MembershipRevokeForm, ReasonForm
from .invitations import accept_invitation, change_membership, create_invitation, invitation_for_token, inviter_authorized, revoke_invitation, revoke_membership, usable_invitations
from .models import Invitation, Membership, User
from .network import client_address
from .permissions import active_context, may_manage_organization
from .services import consume_rate_limit


def admin_context(request):
    context = active_context(request)
    if not may_manage_organization(context):
        raise PermissionDenied("Für diese Aktion fehlt die Organisationsberechtigung.")
    return context


@login_required
@require_http_methods(["GET", "POST"])
def users(request):
    context = admin_context(request)
    form = InvitationForm(request.POST if request.method == "POST" else None, initial={"role": Membership.Role.AUTHOR})
    if request.method == "POST" and form.is_valid():
        if not consume_rate_limit("invitation-sender:" + str(request.user.pk), maximum=20):
            form.add_error(None, "Zu viele Einladungen. Bitte versuchen Sie es später erneut.")
        else:
            try:
                create_invitation(request.user, context, form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            except PermissionDenied:
                raise
            except Exception:
                form.add_error(None, "Die Einladung konnte nicht versendet werden. Bitte prüfen Sie den E-Mail-Versand oder versuchen Sie es später erneut.")
            else:
                messages.success(request, "Einladung versendet. Der Zugriff beginnt erst nach ihrer Annahme und dem eingestellten Beginn.")
                return redirect("users")
    query = request.GET.get("q", "").strip()[:100]
    memberships = Membership.objects.filter(organization=context.organization).select_related("user").order_by("user__last_name", "user__email", "role")
    if query:
        memberships = memberships.filter(Q(user__email__icontains=query) | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))
    page = Paginator(memberships, 20).get_page(request.GET.get("page"))
    now = timezone.now()
    for membership in page:
        membership.access_state = "Entzogen" if membership.revoked_at else "Abgelaufen" if membership.ends_at and membership.ends_at <= now else "Geplant" if membership.starts_at > now else "Aktiv" if membership.user.is_active else "Konto gesperrt"
    invitations = list(Invitation.objects.filter(organization=context.organization)[:20])
    for invitation in invitations:
        invitation.delivery_state = "Angenommen" if invitation.accepted_at else "Zurückgezogen" if invitation.revoked_at else "Abgelaufen" if invitation.expires_at <= now else "Offen"
    return render(request, "users.html", {"context": context, "form": form, "page": page, "invitations": invitations, "query": query})


@login_required
@require_http_methods(["GET", "POST"])
def edit_membership(request, membership_id):
    context = admin_context(request)
    membership = get_object_or_404(Membership.objects.select_related("user"), pk=membership_id, organization=context.organization)
    form = MembershipChangeForm(request.POST if request.method == "POST" else None, initial={
        "role": membership.role, "starts_at": timezone.localtime(membership.starts_at),
        "ends_at": timezone.localtime(membership.ends_at) if membership.ends_at else None,
        "version": membership.version,
    })
    if request.method == "POST" and form.is_valid():
        try:
            change_membership(request.user, context, membership.pk, form.cleaned_data, form.cleaned_data["reason"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Rolle und Gültigkeit aktualisiert.")
            return redirect("users" if may_manage_organization(active_context(request)) else "home")
    return render(request, "membership_form.html", {"context": context, "membership": membership, "form": form, "title": "Rolle bearbeiten", "button": "Änderung speichern"})


@login_required
@require_http_methods(["GET", "POST"])
def remove_membership(request, membership_id):
    context = admin_context(request)
    membership = get_object_or_404(Membership.objects.select_related("user"), pk=membership_id, organization=context.organization)
    form = MembershipRevokeForm(request.POST if request.method == "POST" else None, initial={"version": membership.version})
    if request.method == "POST" and form.is_valid():
        try:
            revoke_membership(request.user, context, membership.pk, form.cleaned_data["reason"], form.cleaned_data["version"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Zugriff entzogen. Andere Organisationsrollen und das persönliche Konto bleiben erhalten.")
            return redirect("users" if may_manage_organization(active_context(request)) else "home")
    return render(request, "membership_form.html", {"context": context, "membership": membership, "form": form, "title": "Zugriff entziehen", "button": "Zugriff jetzt entziehen"})


@login_required
@require_http_methods(["GET", "POST"])
def remove_invitation(request, invitation_id):
    context = admin_context(request)
    invitation = get_object_or_404(Invitation, pk=invitation_id, organization=context.organization)
    form = ReasonForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            revoke_invitation(request.user, context, invitation.pk, form.cleaned_data["reason"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Einladung zurückgezogen.")
            return redirect("users")
    return render(request, "membership_form.html", {"context": context, "invitation": invitation, "form": form, "title": "Einladung zurückziehen", "button": "Einladung zurückziehen"})


@require_http_methods(["GET", "POST"])
def exchange_invitation(request):
    form = InvitationCodeForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if not consume_rate_limit("invite-check:" + client_address(request), maximum=30):
            form.add_error(None, "Zu viele Versuche. Bitte versuchen Sie es später erneut.")
        else:
            invitation = invitation_for_token(form.cleaned_data["token"])
            if invitation:
                request.session.cycle_key()
                request.session["pending_invitation"] = str(invitation.pk)
                return redirect("accept_invitation")
            form.add_error(None, "Einladung ungültig, abgelaufen oder zurückgezogen.")
    return render(request, "invitation_code.html", {"form": form})


@require_http_methods(["GET", "POST"])
def finish_invitation(request):
    invitation_id = request.session.get("pending_invitation")
    if not invitation_id:
        return redirect("exchange_invitation")
    invitation = usable_invitations().select_related("organization").filter(pk=invitation_id).first()
    if not invitation or not inviter_authorized(invitation):
        request.session.pop("pending_invitation", None)
        messages.error(request, "Diese Einladung ist nicht mehr gültig.")
        return redirect("exchange_invitation")
    existing = User.objects.filter(email__iexact=invitation.email).first()
    needs_login = bool(existing and (not request.user.is_authenticated or request.user.pk != existing.pk))
    wrong_account = bool(request.user.is_authenticated and (not existing or request.user.pk != existing.pk))
    form = None if existing else InvitationAccountForm(request.POST if request.method == "POST" else None, email=invitation.email)
    error = None
    if request.method == "POST":
        if needs_login or wrong_account:
            return HttpResponseForbidden("Bitte melden Sie sich mit dem eingeladenen Konto an.")
        if existing or form.is_valid():
            try:
                accept_invitation(invitation.pk, request.user, form.cleaned_data if form else None)
            except (ValidationError, IntegrityError) as problem:
                error = " ".join(problem.messages) if isinstance(problem, ValidationError) else "Das Konto wurde zwischenzeitlich eingerichtet. Melden Sie sich an und nehmen Sie die Einladung erneut an."
            else:
                request.session.pop("pending_invitation", None)
                messages.success(request, "Einladung angenommen. Ihre Rolle ist ab dem vereinbarten Beginn verfügbar.")
                return redirect("home" if request.user.is_authenticated else "sign_in")
    return render(request, "invitation_accept.html", {"invitation": invitation, "form": form, "needs_login": needs_login, "wrong_account": wrong_account, "error": error})
