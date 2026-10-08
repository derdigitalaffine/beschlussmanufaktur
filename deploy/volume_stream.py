"""Read/write only explicit mounted volumes; no network/database/Docker socket."""
import os,sys,tarfile
from pathlib import Path,PurePosixPath
root=Path(sys.argv[2]).resolve()
if not str(root).startswith('/backup/'):raise SystemExit('Unzulässiges Volume.')
if sys.argv[1]=='pack':
    with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():raise SystemExit('Symlinks nicht zulässig.')
            if path.is_file():archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
elif sys.argv[1]=='check-empty':
    if any(root.iterdir()):raise SystemExit('Zielvolume muss leer sein.')
elif sys.argv[1]=='restore':
    if any(root.iterdir()):raise SystemExit('Zielvolume muss leer sein.')
    app_files=str(root)=='/backup/files'
    if app_files:os.chown(root,10001,10001)
    with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as archive:
        count=0
        for member in archive:
            rel=PurePosixPath(member.name)
            if not member.isfile() or rel.is_absolute() or '..' in rel.parts or count>=200000:raise SystemExit('Ungültiger Volumearchiv-Eintrag.')
            path=root.joinpath(*rel.parts);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as out:
                stream=archive.extractfile(member)
                while block:=stream.read(1024*1024):out.write(block)
            path.chmod(member.mode & 0o777)
            if app_files:
                os.chown(path,10001,10001)
                parent=path.parent
                while parent!=root:os.chown(parent,10001,10001);parent=parent.parent
            count+=1
else:raise SystemExit('Unbekannte Aktion.')
