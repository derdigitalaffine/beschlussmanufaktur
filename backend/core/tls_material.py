"""Pure validation, shared by the application and isolated Caddy agent."""
import ipaddress,re
from datetime import datetime,UTC
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ec,ed25519,ed448


def hostname(value):
    if not isinstance(value,str) or len(value)>253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',value) or '..' in value:raise ValueError('Ungültiger Domainname.')
    if value!='localhost' and '.' not in value:raise ValueError('Vollständigen Domainnamen angeben.')
    return value

def certificate(cert_pem,key_pem,domain):
    hostname(domain)
    if len(cert_pem)>150000 or len(key_pem)>20000:raise ValueError('Zertifikatsmaterial zu groß.')
    chain=x509.load_pem_x509_certificates(cert_pem.encode());key=serialization.load_pem_private_key(key_pem.encode(),password=None)
    if not chain or not isinstance(key,(rsa.RSAPrivateKey,ec.EllipticCurvePrivateKey,ed25519.Ed25519PrivateKey,ed448.Ed448PrivateKey)):raise ValueError('Nicht unterstützter Schlüssel.')
    if isinstance(key,rsa.RSAPrivateKey) and key.key_size<2048 or isinstance(key,ec.EllipticCurvePrivateKey) and key.key_size<256:raise ValueError('Schlüssel zu schwach.')
    def public(k):return k.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    if public(key.public_key())!=public(chain[0].public_key()):raise ValueError('Zertifikat und privater Schlüssel passen nicht zusammen.')
    names=chain[0].extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    if not any(name==domain or name.startswith('*.') and domain.endswith(name[1:]) and domain.count('.')==name.count('.') for name in names):raise ValueError('Zertifikat gilt nicht für diese Domain.')
    now=datetime.now(UTC)
    for c in chain:
        if not c.not_valid_before_utc<=now<c.not_valid_after_utc:raise ValueError('Zertifikat ist nicht zeitlich gültig.')
    for child,parent in zip(chain,chain[1:]):
        if child.issuer!=parent.subject:raise ValueError('Zertifikatskette nicht zusammenhängend.')
        if not parent.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:raise ValueError('Aussteller ist keine CA.')
        child.verify_directly_issued_by(parent)
    # Trust at the client remains explicit; private municipal CAs are permitted.
    return {'not_after':chain[0].not_valid_after_utc.isoformat(),'fingerprint':chain[0].fingerprint(__import__('cryptography.hazmat.primitives.hashes',fromlist=['SHA256']).SHA256()).hex()}

def dns_preflight(domain,proof,expected_ips,resolvers=('1.1.1.1','8.8.8.8')):
    import dns.resolver
    hostname(domain)
    expected={str(ipaddress.ip_address(x)) for x in expected_ips}
    if not expected or any(not ipaddress.ip_address(x).is_global for x in expected):raise ValueError('Für HTTP/TLS-ACME sind öffentliche Zieladressen erforderlich.')
    all_addresses=[]
    for server in resolvers:
        resolver=dns.resolver.Resolver(configure=False);resolver.nameservers=[server];resolver.lifetime=3;resolver.timeout=2
        records=resolver.resolve('_beschlussmanufaktur.'+domain,'TXT')
        texts={b''.join(r.strings).decode() for r in records}
        if proof not in texts:raise ValueError('DNS-Besitznachweis fehlt.')
        addresses=set()
        for kind in ('A','AAAA'):
            try:addresses.update(str(ipaddress.ip_address(r.address)) for r in resolver.resolve(domain,kind))
            except dns.resolver.NoAnswer:pass
        if not addresses or not addresses<=expected:raise ValueError('DNS-Zieladressen passen nicht zu den freigegebenen Serveradressen.')
        all_addresses.append(addresses)
    if any(x!=all_addresses[0] for x in all_addresses):raise ValueError('DNS-Resolver melden unterschiedliche Stände.')
    return sorted(all_addresses[0])
