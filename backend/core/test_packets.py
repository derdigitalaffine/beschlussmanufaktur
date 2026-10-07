import io,tempfile
from django.test import TestCase,override_settings
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core import mail
from django.utils import timezone
from pypdf import PdfReader
from .test_meetings import MeetingTests
from .models import TemplateKind,Template,Attachment,InvitationDelivery
from .templates_service import archive
from .meetings_service import save_item,issue,meeting_snapshot
from .invitation_packets import packet,calendar

class PacketTests(MeetingTests):
    def test_combined_pdf_includes_approved_attachment(self):
        with tempfile.TemporaryDirectory() as root,override_settings(MEDIA_ROOT=root):
            kind=TemplateKind.objects.create(organization=self.org,name='Beschluss')
            obj=Template.objects.create(organization=self.org,kind=kind,author=self.clerk,subject='Bau',markdown='Vorlagentext',state='ready')
            a=Attachment(template=obj,name='Anlage.txt',size=10,media_type='text/plain',checked=True,digest=__import__('hashlib').sha256(b'ANLAGENINHALT').hexdigest());a.file.save('private.bin',ContentFile(b'ANLAGENINHALT'));archive(obj,self.clerk,'Bereitgestellt')
            save_item(self.c,self.meeting.pk,1,{'title':'Bau','position':1,'public':True,'template':obj});self.meeting.refresh_from_db()
            invitation=issue(self.c,self.meeting.pk,self.meeting.version)
            result=packet(invitation.snapshot,self.c);reader=PdfReader(io.BytesIO(result));text=''.join(p.extract_text() for p in reader.pages)
            self.assertIn('ANLAGENINHALT',text);self.assertIn('Seite',text);self.assertGreaterEqual(len(reader.pages),2)
    def test_calendar_escaped_and_utc(self):
        data=meeting_snapshot(self.meeting);data['title']='Sitzung\r\nATTENDEE:evil'
        result=calendar(data)
        self.assertIn(b'BEGIN:VCALENDAR',result);self.assertNotIn(b'\r\nATTENDEE:evil',result);self.assertIn(b'DTSTART:',result)
    def test_mail_worker_uses_fixed_recipient_snapshot(self):
        self.item();self.invite();call_command('invitation_worker')
        self.assertTrue(mail.outbox);self.assertTrue(all('GEHEIMER' not in m.body for m in mail.outbox))
        self.assertTrue(InvitationDelivery.objects.filter(delivered_at__isnull=False).exists())
    def test_recipient_cannot_download_after_revocation(self):
        self.item();inv=self.invite();self.c.revoked_at=timezone.now();self.c.save()
        self.assertEqual(self.client.get(f'/einladungen/{inv.pk}/pdf/').status_code,403)
