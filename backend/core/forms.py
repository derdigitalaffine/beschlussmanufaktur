from django import forms
from .models import Organization

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

