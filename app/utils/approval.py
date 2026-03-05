import hashlib
import hmac
import time


def generate_approval_token(secret: str, directory: str, requested_at_epoch: int, reason: str) -> str:
    payload = f"{directory}|{requested_at_epoch}|{reason}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def validate_approval_token(
    secret: str,
    directory: str,
    requested_at_epoch: int,
    reason: str,
    provided_token: str,
    ttl_seconds: int,
    now_epoch: int | None = None,
) -> bool:
    if not secret or not provided_token:
        return False

    now = now_epoch if now_epoch is not None else int(time.time())
    if requested_at_epoch > now:
        return False
    if now - requested_at_epoch > ttl_seconds:
        return False

    expected = generate_approval_token(secret, directory, requested_at_epoch, reason)
    return hmac.compare_digest(expected, provided_token)
