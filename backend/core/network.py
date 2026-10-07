from ipaddress import ip_address
from django.conf import settings


def client_address(request):
    """Forwarded IPs are trusted only in an explicitly private proxy deployment.

    Caddy overwrites untrusted incoming X-Forwarded-For values by default.
    Never enable this when the backend is directly reachable by users.
    """
    peer = request.META.get("REMOTE_ADDR", "unknown")
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[-1].strip()
        try:
            return str(ip_address(forwarded))
        except ValueError:
            pass
    return peer
