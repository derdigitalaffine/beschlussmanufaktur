import importlib.util,sys,io
from pathlib import Path
from datetime import datetime,UTC,timedelta
from unittest.mock import patch
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase
from .tls_material import certificate,hostname
from .models import TLSPlan,User
class TLSMaterialTests(TestCase):
    def material(self,host='rat.example.org'):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,host)])
        cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.now(UTC)-timedelta(days=1)).not_valid_after(datetime.now(UTC)+timedelta(days=30)).add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]),critical=False).sign(key,hashes.SHA256())
        return cert.public_bytes(serialization.Encoding.PEM).decode(),key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
    def test_import_domain_key_match_and_injection(self):
        cert,key=self.material();info=certificate(cert,key,'rat.example.org');self.assertIn('not_after',info)
        with self.assertRaises(ValueError):certificate(cert,key,'other.example.org')
        _,other=self.material()
        with self.assertRaises(ValueError):certificate(cert,other,'rat.example.org')
        for value in ['evil.org { reverse_proxy other }','good.org\n','https://good.org','*.good.org']:
            with self.assertRaises(ValueError):hostname(value)
    def test_agent_generated_config_has_fixed_upstreams_and_unix_admin(self):
        directory=Path(__file__).resolve().parents[2]/'deploy'
        sys.modules['tls_material']=__import__('core.tls_material',fromlist=['certificate'])
        spec=importlib.util.spec_from_file_location('tls_agent',directory/'tls_agent.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rendered=module.render({'rat.example.org':{'role':'public','mode':'internal'}});self.assertIn('unix//runtime/admin.sock',rendered);self.assertIn('public:8000',rendered);self.assertNotIn('backend:8000',rendered)
        with self.assertRaises(ValueError):module.render({'evil.org\n}':{'role':'public','mode':'internal'}})
