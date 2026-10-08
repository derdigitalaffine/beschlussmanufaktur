#!/usr/bin/env python3
"""Local operator only. Never mount Docker's socket into the application."""
import argparse,fcntl,hashlib,json,os,subprocess,sys,tarfile,tempfile
from datetime import datetime,UTC
from pathlib import Path,PurePosixPath
from backup_crypto import read_key,encrypt,decrypt
ROOT=Path(__file__).resolve().parents[1]
STACKS={
 'internal':{'file':'compose.yaml','apps':['backend'],'databases':[('db','beschlussmanufaktur','beschlussmanufaktur')],'volumes':['files','caddy','tls'],'workers':['exchange-worker','notification-worker','invitation-worker','operations-worker','tls-agent','caddy']},
 'external':{'file':'compose.external.yaml','apps':['protected','public'],'databases':[('protected-db','beschlussmanufaktur','protected'),('public-db','beschlussmanufaktur','public')],'volumes':['files','caddy','tls'],'workers':['protected-notification-worker','tls-agent','caddy']}}

class Compose:
 def __init__(self,stack):self.config=STACKS[stack];self.base=['docker','compose','-f',str(ROOT/self.config['file'])]
 def run(self,*args,output=None,input=None):
    result=subprocess.run([*self.base,*args],cwd=ROOT,stdin=input,stdout=output or subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if result.returncode:raise RuntimeError('Compose-Betriebsaktion fehlgeschlagen; Dienstkonfiguration lokal prüfen.')
    return result.stdout.decode().strip() if output is None else ''
 def manage(self,app,*args):return self.run('exec','-T',app,'python','manage.py',*args)

def sha(path):
 value=hashlib.sha256()
 with path.open('rb') as stream:
    while block:=stream.read(1024*1024):value.update(block)
 return value.hexdigest()

def backup(args):
 c=Compose(args.stack);target=Path(args.target).resolve();keyfile=Path(args.key_file).resolve()
 if target==ROOT or ROOT in target.parents or target==keyfile.parent or target in keyfile.parents:raise ValueError('Separates Sicherungsziel und getrennten Schlüsselpfad wählen.')
 target.mkdir(parents=True,exist_ok=True);target.chmod(0o700);key=read_key(keyfile)
 lock=open(target/'.backup.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 running=set(c.run('ps','--status','running','--services').splitlines());apps=c.config['apps'];previous={}
 if not set(apps)<=running:raise ValueError('Fach-/Portaldienste müssen vor der Sicherung laufen.')
 pause=[s for s in c.config['workers'] if s in running]
 # Work directory is private local temporary storage, never the remote backup target.
 with tempfile.TemporaryDirectory(prefix='bm-backup-') as tmp:
    work=Path(tmp);work.chmod(0o700)
    try:
        if pause:c.run('stop',*pause)
        for app in apps:
            previous[app]=c.manage(app,'maintenance','status');c.manage(app,'maintenance','on','--reason','Konsistente Betriebssicherung')
        manifest={'schema':1,'stack':args.stack,'created_at':datetime.now(UTC).isoformat(),'apps':{app:json.loads(c.manage(app,'backup_manifest')) for app in apps},'files':{}}
        for service,user,db in c.config['databases']:
            path=work/(service+'.dump')
            with path.open('wb') as out:c.run('exec','-T',service,'pg_dump','-U',user,'-d',db,'--format=custom','--no-owner',output=out)
        for volume in c.config['volumes']:
            path=work/(volume+'.tar')
            with path.open('wb') as out:c.run('run','-T','--rm','--no-deps','backup-tools','python','volume_stream.py','pack','/backup/'+volume,output=out)
        for path in sorted(work.iterdir()):manifest['files'][path.name]={'sha256':sha(path),'size':path.stat().st_size}
        (work/'manifest.json').write_text(json.dumps(manifest,sort_keys=True))
        archive=work/'archive.tar'
        with tarfile.open(archive,'w') as tar:
            for name in ['manifest.json',*manifest['files']]:tar.add(work/name,arcname=name,recursive=False)
        name='bm-'+args.stack+'-'+datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')+'.bmbak';partial=target/(name+'.partial');final=target/name
        encrypt(archive,partial,key,{'schema':1,'stack':args.stack,'created_at':manifest['created_at']});partial.replace(final)
        # Immediate authenticated readback and full manifest integrity check.
        validate(final,key,work/'verified')
        status={'ok':True,'created_at':manifest['created_at'],'stack':args.stack,'archive':name,'sha256':sha(final)}
        write_status(target,status)
        if args.status_file:write_summary(args.status_file,status)
        print(str(final))
    except Exception:
        status={'ok':False,'created_at':datetime.now(UTC).isoformat(),'stack':args.stack,'error':'Sicherung fehlgeschlagen; lokalen Betriebszustand prüfen.'}
        write_status(target,status)
        if args.status_file:write_summary(args.status_file,status)
        raise
    finally:
        for app,state in previous.items():
            if state=='off':c.manage(app,'maintenance','off')
        if pause:c.run('start',*pause)

def write_summary(filename,status):
 path=Path(filename);path.parent.mkdir(parents=True,exist_ok=True);path.parent.chmod(0o755)
 tmp=path.with_suffix('.new');tmp.write_text(json.dumps({k:status[k] for k in ('ok','created_at','stack')}));tmp.chmod(0o644);tmp.replace(path)

def write_status(target,status):
 tmp=target/'last-backup.new';tmp.write_text(json.dumps(status));tmp.chmod(0o600);tmp.replace(target/'last-backup.json')

def validate(archive,key,destination):
 destination=Path(destination);destination.mkdir(mode=0o700,parents=True,exist_ok=False);plain=destination/'archive.tar';metadata=decrypt(archive,plain,key)
 with tarfile.open(plain,'r:') as tar:
    members=tar.getmembers()
    if len(members)>20:raise ValueError('Zu viele Sicherungsbestandteile.')
    for member in members:
        name=PurePosixPath(member.name)
        if not member.isfile() or name.is_absolute() or len(name.parts)!=1 or member.size>128*1024**3:raise ValueError('Unzulässiger Sicherungseintrag.')
        path=destination/member.name
        if path.exists():raise ValueError('Doppelter Sicherungseintrag.')
        with path.open('xb') as out:
            stream=tar.extractfile(member)
            while block:=stream.read(1024*1024):out.write(block)
        path.chmod(0o600)
 manifest=json.loads((destination/'manifest.json').read_text())
 if manifest['schema']!=1 or manifest['stack']!=metadata['stack'] or set(manifest['files'])!=set(m.name for m in members)-{'manifest.json'}:raise ValueError('Sicherungsmanifest widersprüchlich.')
 for name,value in manifest['files'].items():
    path=destination/name
    if path.stat().st_size!=value['size'] or sha(path)!=value['sha256']:raise ValueError('Prüfsumme einer Sicherung stimmt nicht.')
 plain.unlink();return manifest

def restore(args):
 key=read_key(args.key_file);destination=Path(args.destination).resolve()
 if destination.exists():raise ValueError('Prüfziel muss neu und leer sein.')
 manifest=validate(args.archive,key,destination)
 if manifest['stack']!=args.stack:raise ValueError('Sicherung gehört zum anderen Stack.')
 if not args.apply:print('Authentifizierte Sicherung vollständig geprüft: '+str(destination));return
 c=Compose(args.stack);running=set(c.run('ps','--status','running','--services').splitlines())
 if running-set(x[0] for x in c.config['databases']):raise ValueError('Restore nur auf neuem Ziel mit ausschließlich laufenden Datenbanken.')
 # Build missing target images separately: BuildKit progress is not manifest JSON.
 c.run('build',*c.config['apps'],'restore-tools')
 for app,code in manifest['apps'].items():
    current=json.loads(c.run('run','-T','--rm','--no-deps',app,'python','manage.py','backup_manifest'))
    if current!=code:raise ValueError('Code-/Migrationsstand abweichend. Passenden Release bereitstellen.')
 for service,user,db in c.config['databases']:
    count=c.run('exec','-T',service,'psql','-U',user,'-d',db,'-Atc',"SELECT count(*) FROM pg_tables WHERE schemaname='public'")
    if count!='0':raise ValueError('Zieldatenbank nicht leer; kein Überschreiben bestehender Installation.')
 for service,user,db in c.config['databases']:
    with (destination/(service+'.dump')).open('rb') as inp:c.run('exec','-T',service,'pg_restore','-U',user,'-d',db,'--no-owner','--exit-on-error',input=inp)
 for volume in c.config['volumes']:
    with (destination/(volume+'.tar')).open('rb') as inp:c.run('run','-T','--rm','--no-deps','restore-tools','python','volume_stream.py','restore','/backup/'+volume,input=inp)
 # Backup maintenance flags deliberately remain active; never auto-publish after restore.
 print('Restore auf leerem Ziel abgeschlossen. Vor Start Rechte, Journale, Veröffentlichungen und Laufzeitschlüssel prüfen; Wartung bleibt aktiv.')

def main():
 parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
 p=sub.add_parser('backup');p.add_argument('--target',required=True);p.add_argument('--status-file')
 r=sub.add_parser('restore');r.add_argument('--archive',required=True);r.add_argument('--destination',required=True);r.add_argument('--apply',action='store_true')
 for item in (p,r):item.add_argument('--stack',choices=STACKS,required=True);item.add_argument('--key-file',required=True)
 args=parser.parse_args()
 try:(backup if args.operation=='backup' else restore)(args)
 except Exception as exc:print(str(exc),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
