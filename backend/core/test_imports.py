import os
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.test import TestCase
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from .models import Organization,User,Membership,ImportBatch,RegistryRecord,InvitationDispatch,Invitation
from .imports import parse_upload,apply,digest
from .account_mail import send_pending
class ImportTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='VG',kind='association');self.user=User.objects.create_user('admin',email='admin@example.invalid');self.ctx=Membership.objects.create(user=self.user,organization=self.org,role='organization_admin')
    def stage(self,text,kind):
        rows=parse_upload(SimpleUploadedFile('import.csv',text.encode()),kind,self.org)
        return ImportBatch.objects.create(organization=self.org,owner=self.user,context=self.ctx,kind=kind,rows=rows,digest=digest(rows))
    def test_atomic_preview_apply_retry_and_duplicate(self):
        batch=self.stage('kind,name,starts_on,ends_on,details\ncommittee,Rat,,,\n','registry');self.assertEqual(RegistryRecord.objects.count(),0)
        apply(self.ctx,batch.pk);apply(self.ctx,batch.pk);self.assertEqual(RegistryRecord.objects.count(),1)
        with self.assertRaises(ValidationError):self.stage('kind,name,starts_on,ends_on,details\ncommittee,Rat,,,\n','registry')
    def test_current_permissions_and_digest_required(self):
        batch=self.stage('kind,name,starts_on,ends_on,details\ncommittee,Rat,,,\n','registry');batch.digest='x'*64;batch.save()
        with self.assertRaises(ValidationError):apply(self.ctx,batch.pk)
        self.ctx.role='author';self.ctx.save()
        with self.assertRaises(PermissionDenied):apply(self.ctx,batch.pk)
        self.assertEqual(RegistryRecord.objects.count(),0)
    def test_accounts_atomic_encrypted_outbox_no_preview_mail(self):
        batch=self.stage('email,role,starts_at,ends_at\nperson@example.invalid,member,2026-01-01T00:00:00+00:00,\n','accounts')
        with patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':Fernet.generate_key().decode()}):
            apply(self.ctx,batch.pk);self.assertEqual(len(mail.outbox),0);obj=InvitationDispatch.objects.get();self.assertNotIn('person',obj.encrypted_token);self.assertEqual(User.objects.count(),1)
            send_pending();self.assertEqual(len(mail.outbox),1);obj.refresh_from_db();self.assertEqual(obj.encrypted_token,'');send_pending();self.assertEqual(len(mail.outbox),1)
    def test_missing_key_rolls_back_and_duplicate_csv_rejected(self):
        batch=self.stage('email,role,starts_at,ends_at\nperson@example.invalid,member,2026-01-01T00:00:00+00:00,\n','accounts')
        with patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':''}):
            with self.assertRaises(ValidationError):apply(self.ctx,batch.pk)
        self.assertEqual(Invitation.objects.count(),0)
        with self.assertRaises(ValidationError):self.stage('kind,name,starts_on,ends_on,details\ncommittee,Rat,,,\ncommittee,rat,,,\n','registry')
