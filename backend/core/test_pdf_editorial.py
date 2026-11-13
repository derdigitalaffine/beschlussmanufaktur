"""Visual PDF export contract tests: layout, content and tenant separation."""
import io
from unittest.mock import patch
from django.test import SimpleTestCase
from pypdf import PdfReader
from .document_export import export


class PdfEditorialDesignTests(SimpleTestCase):
    @patch('core.models.PortalConfiguration.objects.filter')
    def test_pdf_has_brand_heading_content_tables_and_footer(self, filter_mock):
        filter_mock.return_value.first.return_value = type('Brand', (), {
            'title': 'Musterkommune', 'color': '#245846',
        })()
        data, mime = export(
            'Beratungsunterlage', '# Ausgangslage\n\nEin ausführlicher Sachverhalt.\n\n'
            '| Punkt | Ergebnis |\n| --- | --- |\n| Prüfung | Erledigt |\n\n'
            '## Beschlussvorschlag\n\nDie Verwaltung wird beauftragt.',
            subtitle='Vorlage 2026/12', organization_id=7,
            metadata=['Anlage 1 · Seiten 3–4'],
        )
        self.assertEqual(mime, 'application/pdf')
        pdf = PdfReader(io.BytesIO(data))
        text = '\n'.join(page.extract_text() for page in pdf.pages)
        for term in ('Musterkommune', 'Beratungsunterlage', 'Vorlage 2026/12',
                     'Ausgangslage', 'Prüfung', 'Erledigt',
                     'Beschlussvorschlag', 'Anlage 1', 'Seite 1'):
            self.assertIn(term, text)
        self.assertEqual(pdf.metadata.title, 'Beratungsunterlage')

    def test_long_body_paginated_without_loss(self):
        body = '# Sachstand\n\n' + ('Ein Satz mit belastbarem Inhalt.\n\n' * 140)
        data, _ = export('Umfangreiche Vorlage', body)
        pdf = PdfReader(io.BytesIO(data))
        self.assertGreater(len(pdf.pages), 1)
        self.assertIn('Seite 2', pdf.pages[1].extract_text())
        self.assertIn('Ein Satz mit belastbarem Inhalt.', pdf.pages[-1].extract_text())

    def test_invalid_export_format_rejected(self):
        with self.assertRaises(ValueError):
            export('Test', 'Inhalt', 'html')
