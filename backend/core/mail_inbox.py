"""TLS IMAP polling. Incoming mail never changes invitations or business records."""
import email,hashlib,imaplib,os,re,ssl
from email import policy
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import MailReceipt,MailCursor,Organization

MAX_BYTES=2*1024*1024

def ingest(organization,mailbox,validity,uid,raw,oversized=False):
    if oversized:values={'category':'too_large','subject':'Nachricht überschreitet Empfangsgrenze','sender':'','preview':''}
    else:
        if len(raw)>MAX_BYTES:raise ValidationError('Nachricht zu groß.')
        message=email.message_from_bytes(raw,policy=policy.default)
        parts=list(message.walk())
        text=next((p.get_content() for p in parts if p.get_content_type()=='text/plain' and p.get_content_disposition()!='attachment'),'')
        if not isinstance(text,str):text=''
        values={'category':'delivery_report' if any(p.get_content_type()=='message/delivery-status' for p in parts) else 'unassigned','subject':str(message.get('subject',''))[:200],'sender':str(message.get('from',''))[:200],'preview':text[:4000]}
    return MailReceipt.objects.get_or_create(mailbox=mailbox,uidvalidity=validity,uid=uid,defaults={'organization':organization,**values})[0]

def poll():
    if settings.SERVER_ROLE!='internal':raise ValidationError('IMAP nur auf dem internen Server.')
    host=os.environ.get('IMAP_HOST','');user=os.environ.get('IMAP_USER','');folder=os.environ.get('IMAP_FOLDER','INBOX')
    if not host:return 0
    if any(c in host+folder for c in '\r\n\x00'):raise ValidationError('Ungültige Mailkonfiguration.')
    org=Organization.objects.get(pk=os.environ.get('IMAP_ORGANIZATION',''))
    mailbox=hashlib.sha256((host+'\0'+user+'\0'+folder).encode()).hexdigest()
    conn=imaplib.IMAP4_SSL(host,int(os.environ.get('IMAP_PORT','993')),ssl_context=ssl.create_default_context(),timeout=15)
    try:
        conn.login(user,os.environ.get('IMAP_PASSWORD',''));status,_=conn.select(folder,readonly=True)
        if status!='OK':raise ValidationError('IMAP-Ordner nicht lesbar.')
        validity=int(conn.response('UIDVALIDITY')[1][0]);cursor,_=MailCursor.objects.get_or_create(mailbox=mailbox,defaults={'uidvalidity':validity})
        last=cursor.last_uid if cursor.uidvalidity==validity else 0
        status,rows=conn.uid('search',None,'UID',str(last+1)+':*')
        if status!='OK':raise ValidationError('IMAP-Suche fehlgeschlagen.')
        count=0
        for uid in sorted(int(x) for x in rows[0].split() if int(x)>last)[:50]:
            status,size_rows=conn.uid('fetch',str(uid),'(RFC822.SIZE)')
            if status!='OK':raise ValidationError('IMAP-Metadaten fehlen.')
            header=b' '.join(x for x in size_rows if isinstance(x,bytes));match=re.search(rb'RFC822.SIZE (\d+)',header)
            if not match:raise ValidationError('IMAP-Größenprüfung fehlgeschlagen.')
            oversized=int(match.group(1))>MAX_BYTES;raw=b''
            if not oversized:
                status,content=conn.uid('fetch',str(uid),'(BODY.PEEK[])')
                if status!='OK':raise ValidationError('IMAP-Nachricht nicht abrufbar.')
                raw=b''.join(x[1] for x in content if isinstance(x,tuple))
            with transaction.atomic():
                cursor=MailCursor.objects.select_for_update().get(pk=mailbox)
                ingest(org,mailbox,validity,uid,raw,oversized)
                previous=cursor.last_uid if cursor.uidvalidity==validity else 0;cursor.uidvalidity=validity;cursor.last_uid=max(uid,previous);cursor.save()
            count+=1
        return count
    finally:
        try:conn.logout()
        except (OSError,imaplib.IMAP4.error):pass
