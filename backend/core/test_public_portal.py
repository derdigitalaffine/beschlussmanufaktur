import uuid
from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from .models import PublicRecord
from .public_portal import selection,calendar_feed,api,validate_metadata
class PortalTests(TestCase):
    def setUp(self):
        self.org=uuid.uuid4();self.committee=uuid.uuid4();self.rf=RequestFactory()
        self.record=PublicRecord.objects.create(id=uuid.uuid4(),organization_id=self.org,kind='meeting',title='Rat öffentlich',body='Öffentlicher Haushaltsplan',metadata={'starts_at':'2026-10-08T18:00:00+02:00','ends_at':'2026-10-08T20:00:00+02:00','location':'Saal\nBEGIN:VEVENT','committee_id':str(self.committee)})
    def test_search_and_filters(self):
        for params in [{'q':'Haushalt'},{'organisation':str(self.org),'gremium':str(self.committee)},{'von':'2026-10-08','bis':'2026-10-08'}]:self.assertEqual(list(selection(self.rf.get('/',params))),[self.record])
        for params in [{'organisation':'invalid'},{'von':'2026-02-30'},{'bis':'2026-10-07'},{'art':'password'}]:self.assertFalse(selection(self.rf.get('/',params)).exists())
    def test_calendar_escaped_and_api_allowlist(self):
        data=calendar_feed(self.rf.get('/')).content.decode();self.assertEqual(data.count('\r\nBEGIN:VEVENT\r\n'),1);self.assertIn('DTSTART:20261008T160000Z',data)
        response=api(self.rf.get('/'));self.assertNotIn(b'password',response.content);self.assertIn(b'bm-public-v1',response.content)
    def test_metadata_rejects_extra_private_fields_and_naive_time(self):
        with self.assertRaises(ValidationError):validate_metadata({'private':'secret'},'meeting')
        with self.assertRaises(ValidationError):validate_metadata(dict(self.record.metadata,starts_at='2026-10-08T18:00:00'),'meeting')
