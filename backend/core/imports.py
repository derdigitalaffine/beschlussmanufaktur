"""Scoped, validated import staging. No arbitrary fields, updates or passwords."""
import csv,hashlib,io,json,uuid
from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime,parse_date
from django.views.decorators.http import require_http_methods
from .models import ImportBatch,RegistryRecord,PersonProfile,Membership,AuditEvent,Invitation,InvitationDispatch
from .invitations import lock_admin,check_existing_role,digest_token,usable_invitations
from .user_views import admin_context

HEADERS={'registry':{'kind','name','starts_on','ends_on','details'},'people':{'name','email','function','faction'},'accounts':{'email','role','starts_at','ends_at'}}

def digest(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def parse_upload(upload,kind,organization):
    if upload.size>500_000:raise ValidationError('CSV maximal 500 kB.')
    try:text=upload.read().decode('utf-8-sig')
    except UnicodeError:raise ValidationError('CSV benötigt UTF-8.')
    try:
        delimiter=';' if ';' in text.splitlines()[0] else ','
        reader=csv.DictReader(io.StringIO(text),delimiter=delimiter)
        if set(reader.fieldnames or [])!=HEADERS[kind] or len(reader.fieldnames)!=len(HEADERS[kind]):raise ValidationError('CSV-Spalten stimmen nicht mit der Vorlage überein.')
        rows=list(reader)
    except (csv.Error,IndexError):raise ValidationError('CSV nicht lesbar.')
    if not rows or len(rows)>200:raise ValidationError('CSV benötigt 1 bis 200 Zeilen.')
    seen=set()
    for i,row in enumerate(rows,2):
        if None in row or any(v is None for v in row.values()):raise ValidationError(f'Zeile {i}: unvollständige Spalten.')
        row.update({k:v.strip() for k,v in row.items()})
        if kind=='registry':
            if row['kind'] not in RegistryRecord.Kind.values:raise ValidationError(f'Zeile {i}: unbekannte Stammdatenart.')
            key=(row['kind'],row['name'].casefold())
            if RegistryRecord.objects.filter(organization=organization,kind=row['kind'],name__iexact=row['name']).exists():raise ValidationError(f'Zeile {i}: Stammdatendublette, bitte bestehenden Datensatz bearbeiten.')
            values=dict(row)
            for field in ('starts_on','ends_on'):
                try:value=parse_date(row[field]) if row[field] else None
                except ValueError:value=None
                if row[field] and not value:raise ValidationError(f'Zeile {i}: Datum ungültig.')
                values[field]=value
            RegistryRecord(organization=organization,**values).full_clean()
        elif kind=='people':
            key=row['name'].casefold()
            if PersonProfile.objects.filter(organization=organization,name__iexact=row['name']).exists():raise ValidationError(f'Zeile {i}: Personenname bereits vorhanden; Identität manuell prüfen.')
            if row['email']:validate_email(row['email']);row['email']=row['email'].lower()
            PersonProfile(organization=organization,name=row['name'],function=row['function'],faction=row['faction']).full_clean()
        else:
            validate_email(row['email']);row['email']=row['email'].lower();key=(row['email'],row['role'])
            if row['role'] not in set(Membership.Role.values)-{'emergency'}:raise ValidationError(f'Zeile {i}: Rolle ungültig.')
            start=parse_datetime(row['starts_at']) if row['starts_at'] else timezone.now()
            end=parse_datetime(row['ends_at']) if row['ends_at'] else None
            if not start or start.utcoffset() is None or row['ends_at'] and (not end or end.utcoffset() is None) or end and end<=start:raise ValidationError(f'Zeile {i}: Zeitraum mit Zeitzone angeben.')
            row['starts_at']=start.isoformat();row['ends_at']=end.isoformat() if end else ''
            check_existing_role(organization,row['email'],row['role'])
            if usable_invitations().filter(organization=organization,email=row['email'],role=row['role']).exists():raise ValidationError(f'Zeile {i}: Einladung bereits vorhanden.')
        if key in seen:raise ValidationError(f'Zeile {i}: Dublette innerhalb der CSV.')
        seen.add(key)
    return rows

@transaction.atomic
def apply(context,batch_id):
    lock_admin(context.user,context.pk,context.organization_id)
    batch=ImportBatch.objects.select_for_update().get(pk=batch_id,organization=context.organization,owner=context.user,context=context)
    if batch.applied_at:return batch
    if batch.created_at<timezone.now()-timedelta(hours=24) or batch.digest!=digest(batch.rows):raise ValidationError('Importvorschau abgelaufen oder verändert.')
    # Validate again against current database state before any mutation.
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=sorted(HEADERS[batch.kind]));writer.writeheader();writer.writerows(batch.rows)
    from django.core.files.uploadedfile import SimpleUploadedFile
    rows=parse_upload(SimpleUploadedFile('review.csv',stream.getvalue().encode()),batch.kind,context.organization)
    for row in rows:
        if batch.kind=='registry':
            values=dict(row)
            for field in ('starts_on','ends_on'):values[field]=parse_date(row[field]) if row[field] else None
            obj=RegistryRecord(organization=context.organization,**values);obj.full_clean();obj.save()
        elif batch.kind=='people':
            from .models import User
            # Reuse central account only when already related to this organization.
            user=User.objects.filter(email=row['email'],memberships__organization=context.organization).distinct().first() if row['email'] else None
            profile=PersonProfile(organization=context.organization,user=user,name=row['name'],function=row['function'],faction=row['faction'])
            from .identities import assign
            assign(profile);profile.save()
        else:
            import secrets
            from .secret_store import encrypt
            token=secrets.token_urlsafe(32)
            invitation=Invitation(organization=context.organization,email=row['email'],role=row['role'],starts_at=parse_datetime(row['starts_at']),ends_at=parse_datetime(row['ends_at']) if row['ends_at'] else None,invited_by=context.user,token_digest=digest_token(token),expires_at=timezone.now()+timedelta(days=7))
            invitation.full_clean();invitation.save();InvitationDispatch.objects.create(invitation=invitation,encrypted_token=encrypt(token))
    batch.applied_at=timezone.now();batch.save(update_fields=['applied_at']);AuditEvent.objects.create(actor=context.user,action='import.applied',object_id=str(batch.pk),metadata={'kind':batch.kind,'rows':len(rows),'digest':batch.digest})
    return batch

class UploadForm(forms.Form):
    kind=forms.ChoiceField(label='Importart',choices=[('registry','Gremien und Stammdaten'),('people','Personenprofile'),('accounts','Konten/Rollen als Einladungen')])
    file=forms.FileField(label='UTF-8-CSV')

@login_required
@require_http_methods(['GET','POST'])
def workspace(request,batch_id=None):
    context=admin_context(request);batch=get_object_or_404(ImportBatch,pk=batch_id,organization=context.organization,owner=request.user,context=context) if batch_id else None;form=UploadForm(request.POST or None,request.FILES or None)
    error=''
    if request.method=='POST':
        try:
            if batch:
                if request.POST.get('confirm')!='yes':raise ValidationError('Vorschau ausdrücklich bestätigen.')
                apply(context,batch.pk);return redirect('import_detail',batch_id=batch.pk)
            if form.is_valid():
                rows=parse_upload(form.cleaned_data['file'],form.cleaned_data['kind'],context.organization)
                with transaction.atomic():
                    lock_admin(request.user,context.pk,context.organization_id)
                    batch=ImportBatch.objects.create(organization=context.organization,owner=request.user,context=context,kind=form.cleaned_data['kind'],rows=rows,digest=digest(rows))
                return redirect('import_detail',batch_id=batch.pk)
        except (ValidationError,ValueError) as exc:error=' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Datum oder Eingabewert ungültig.'
    return render(request,'imports.html',{'context':context,'form':form,'batch':batch,'error':error,'headers':HEADERS})
