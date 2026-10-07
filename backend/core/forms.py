from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import Membership, Organization, User

class SignInForm(forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(label="Passwort", max_length=256, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

class CodeForm(forms.Form):
    code = forms.RegexField(r"^[0-9]{6}$", label="Anmeldecode", max_length=6, widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}))

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "kind"]
        labels = {"name": "Bezeichnung", "kind": "Organisationstyp"}


class MembershipPeriodForm(forms.Form):
    role = forms.ChoiceField(label="Rolle", choices=Membership.Role.choices)
    starts_at = forms.DateTimeField(label="Gültig ab", required=False,
        input_formats=["%Y-%m-%dT%H:%M"], widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"))
    ends_at = forms.DateTimeField(label="Gültig bis (optional)", required=False,
        input_formats=["%Y-%m-%dT%H:%M"], widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"))

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("starts_at") or timezone.now()
        cleaned["starts_at"] = start
        end = cleaned.get("ends_at")
        if end and (end <= start or end <= timezone.now()):
            self.add_error("ends_at", "Das Ende muss nach dem Beginn und in der Zukunft liegen.")
        return cleaned


class InvitationForm(MembershipPeriodForm):
    email = forms.EmailField(label="E-Mail-Adresse", max_length=254)
    field_order = ["email", "role", "starts_at", "ends_at"]

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Begründung", max_length=500, widget=forms.Textarea(attrs={"rows": 3}))


class MembershipChangeForm(MembershipPeriodForm):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    reason = forms.CharField(label="Begründung der Änderung", max_length=500, widget=forms.Textarea(attrs={"rows": 3}))


class MembershipRevokeForm(ReasonForm):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)


class InvitationCodeForm(forms.Form):
    token = forms.RegexField(r"^[A-Za-z0-9_-]{43}$", label="Einladungscode", max_length=43,
        widget=forms.TextInput(attrs={"autocomplete": "off", "id": "invitation-token"}))


class InvitationAccountForm(forms.Form):
    first_name = forms.CharField(label="Vorname", max_length=150)
    last_name = forms.CharField(label="Nachname", max_length=150)
    password = forms.CharField(label="Passwort", max_length=256,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password_confirm = forms.CharField(label="Passwort wiederholen", max_length=256,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, email, **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        if password:
            validate_password(password, User(email=self.email, first_name=cleaned.get("first_name", ""), last_name=cleaned.get("last_name", "")))
        if password and password != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Die Passwörter stimmen nicht überein.")
        return cleaned
