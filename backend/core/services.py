import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AuditEvent, EmailChallenge, LoginRateLimit


def consume_rate_limit(identifier, maximum=10):
    key = salted_hmac("login-rate-limit", identifier).hexdigest()
    with transaction.atomic():
        LoginRateLimit.objects.get_or_create(key=key)
        bucket = LoginRateLimit.objects.select_for_update().get(key=key)
        now = timezone.now()
        if now - bucket.window_start >= timedelta(minutes=15):
            bucket.window_start, bucket.attempts = now, 0
        allowed = bucket.attempts < maximum
        if allowed:
            bucket.attempts += 1
        bucket.save(update_fields=["window_start", "attempts"])
        return allowed


def issue_challenge(user):
    code = f"{secrets.randbelow(1000000):06d}"
    challenge = EmailChallenge.objects.create(
        user=user, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=5),
    )
    try:
        send_mail("Ihr Anmeldecode für Beschlussmanufaktur", f"Ihr Anmeldecode lautet: {code}\n\nEr gilt fünf Minuten. Geben Sie ihn nicht weiter.", None, [user.email])
    except Exception:
        # A delivery failure must never yield an authenticated or usable challenge.
        challenge.delete()
        raise
    return challenge


def verify_challenge(challenge_id, code):
    with transaction.atomic():
        challenge = EmailChallenge.objects.select_for_update().select_related("user").filter(pk=challenge_id).first()
        now = timezone.now()
        if not challenge or challenge.consumed_at or challenge.expires_at <= now or challenge.attempts >= 5:
            return None
        challenge.attempts += 1
        valid = check_password(code, challenge.code_hash) and challenge.user.is_active
        if valid:
            challenge.consumed_at = now
        challenge.save(update_fields=["attempts", "consumed_at"])
        if valid:
            AuditEvent.objects.create(actor=challenge.user, action="authentication.email_verified")
            return challenge.user
        return None

