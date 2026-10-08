import importlib.util,sys,tempfile,json,tarfile,io,os
from pathlib import Path
from django.test import SimpleTestCase
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'ops'))
from backup_crypto import encrypt,decrypt
from backup import validate,sha
class BackupCryptoTests(SimpleTestCase):
    def test_streaming_authenticated_roundtrip_tamper_and_no_existing_target_delete(self):
        with tempfile.TemporaryDirectory(dir=root,prefix='.backup-test-') as tmp:
            p=Path(tmp);source=p/'plain';source.write_bytes(os.urandom(3*1024*1024));key=os.urandom(32);archive=p/'safe';encrypt(source,archive,key,{'schema':1,'stack':'internal'});self.assertNotIn(source.read_bytes()[:50],archive.read_bytes());decrypt(archive,p/'restored',key);self.assertEqual(sha(source),sha(p/'restored'))
            with self.assertRaises(ValueError):decrypt(archive,p/'restored',key)
            self.assertTrue((p/'restored').exists());data=bytearray(archive.read_bytes());data[-20]^=1;(p/'bad').write_bytes(data)
            with self.assertRaises(Exception):decrypt(p/'bad',p/'rejected',key)
            self.assertFalse((p/'rejected').exists())
    def test_restore_manifest_and_traversal_rejection(self):
        with tempfile.TemporaryDirectory(dir=root,prefix='.backup-test-') as tmp:
            p=Path(tmp);payload=p/'db.dump';payload.write_bytes(b'database fixture');manifest={'schema':1,'stack':'internal','files':{'db.dump':{'sha256':sha(payload),'size':payload.stat().st_size}}};(p/'manifest.json').write_text(json.dumps(manifest));tar=p/'bundle'
            with tarfile.open(tar,'w') as out:
                out.add(payload,arcname='db.dump');out.add(p/'manifest.json',arcname='manifest.json')
            key=os.urandom(32);encrypt(tar,p/'safe',key,{'stack':'internal'});self.assertEqual(validate(p/'safe',key,p/'verified')['stack'],'internal')
            with tarfile.open(p/'evil-tar','w') as out:
                info=tarfile.TarInfo('../escape');info.size=1;out.addfile(info,io.BytesIO(b'x'))
            encrypt(p/'evil-tar',p/'evil',key,{'stack':'internal'})
            with self.assertRaises(ValueError):validate(p/'evil',key,p/'rejected')
            self.assertFalse((p/'escape').exists())
