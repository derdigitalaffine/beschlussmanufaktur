"""Streaming AES-256-GCM envelope. Decryption is verified before archive use."""
import base64,json,os,struct
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
MAGIC=b'BMBAK1\0'
BLOCK=1024*1024

def read_key(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_mode & 0o077:raise ValueError('Schlüsseldatei muss privat (0600) sein.')
    value=base64.urlsafe_b64decode(path.read_bytes().strip())
    if len(value)!=32:raise ValueError('Sicherungsschlüssel benötigt 256 Bit.')
    return value

def encrypt(source,target,key,metadata):
    header=json.dumps(metadata,sort_keys=True,separators=(',',':')).encode()
    if len(header)>4096:raise ValueError('Metadaten zu groß.')
    prefix=MAGIC+struct.pack('>I',len(header))+header;nonce=os.urandom(12)
    enc=Cipher(algorithms.AES(key),modes.GCM(nonce)).encryptor();enc.authenticate_additional_data(prefix)
    with open(source,'rb') as inp,open(target,'xb') as out:
        out.write(prefix);out.write(nonce)
        while data:=inp.read(BLOCK):out.write(enc.update(data))
        out.write(enc.finalize());out.write(enc.tag)
    Path(target).chmod(0o600)

def decrypt(source,target,key):
    target=Path(target)
    if target.exists():raise ValueError('Entschlüsselungsziel muss neu sein.')
    try:
        with open(source,'rb') as inp:
            if inp.read(len(MAGIC))!=MAGIC:raise ValueError('Unbekanntes Sicherungsformat.')
            length=struct.unpack('>I',inp.read(4))[0]
            if length>4096:raise ValueError('Ungültige Sicherungsmetadaten.')
            header=inp.read(length);metadata=json.loads(header);prefix=MAGIC+struct.pack('>I',length)+header;nonce=inp.read(12)
            start=inp.tell();size=Path(source).stat().st_size;remaining=size-start-16
            if remaining<0:raise ValueError('Sicherung unvollständig.')
            inp.seek(-16,2);tag=inp.read(16);inp.seek(start)
            dec=Cipher(algorithms.AES(key),modes.GCM(nonce,tag)).decryptor();dec.authenticate_additional_data(prefix)
            with target.open('xb') as out:
                target.chmod(0o600)
                while remaining:
                    data=inp.read(min(BLOCK,remaining))
                    if not data:raise ValueError('Sicherung abgeschnitten.')
                    out.write(dec.update(data));remaining-=len(data)
                out.write(dec.finalize())
            return metadata
    except Exception:
        target.unlink(missing_ok=True);raise
