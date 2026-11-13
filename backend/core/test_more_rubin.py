from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from .more_rubin import convert_people_csv
from .imports import parse_upload
from .models import Organization


class MoreRubinCSVTests(TestCase):
    def test_person_export_normalizes_into_existing_import_pipeline(self):
        org = Organization.objects.create(name="Test", kind="association")
        raw = "Vorname;Nachname;E-Mail;Funktion;Fraktion\nAda;Muster;ADA@example.invalid;Mitglied;Liste A\n"
        data = convert_people_csv(SimpleUploadedFile("more.csv", raw.encode()))
        rows = parse_upload(SimpleUploadedFile("normalized.csv", data), "people", org)
        self.assertEqual(rows[0]["name"], "Ada Muster")
        self.assertEqual(rows[0]["email"], "ada@example.invalid")
        self.assertEqual(rows[0]["faction"], "Liste A")

    def test_rejects_unknown_columns_instead_of_silently_dropping_data(self):
        raw = "Vorname;Nachname;Geburtsdatum\nAda;Muster;2000-01-01\n"
        with self.assertRaises(ValidationError):
            convert_people_csv(SimpleUploadedFile("more.csv", raw.encode()))

    def test_rejects_ambiguous_email_columns(self):
        raw = "Name;Email;E-Mail\nAda Muster;a@example.invalid;b@example.invalid\n"
        with self.assertRaises(ValidationError):
            convert_people_csv(SimpleUploadedFile("more.csv", raw.encode()))
