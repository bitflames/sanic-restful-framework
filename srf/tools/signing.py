import base64
import hashlib
import hmac
import time
from typing import Union

Secret = Union[str, bytes]


def _b64encode(value: str) -> str:
    """Encode Unicode text as an unpadded, URL-safe Base64 ASCII string.

    UTF-8 converts the original Python string into bytes without restricting
    the value to English characters. Base64 itself always produces ASCII, so
    decoding the result with ASCII documents and enforces that guarantee.
    """
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _b64decode(value: str) -> str:
    """Decode an unpadded, URL-safe Base64 string back into Unicode text."""
    padding = "=" * (-len(value) % 4)
    decoded = base64.b64decode(
        value + padding,
        altchars=b"-_",
        validate=True,
    )
    return decoded.decode("utf-8")


def _secret_bytes(secret_key: Secret) -> bytes:
    """Convert a text secret to UTF-8 bytes while preserving byte secrets."""
    secret = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
    if not secret:
        raise ValueError("secret_key must not be empty")
    return secret


def sign_state(
    state: str,
    secret_key: Secret,
    *,
    issued_at: int | None = None,
) -> str:
    """Create a signed OAuth state token.

    Args:
        state: The random OAuth state value sent to the authorization server.
            Generate it with a cryptographically secure function such as
            ``secrets.token_urlsafe(32)``. It must not be empty.
        secret_key: The private HMAC key used to sign the token. Pass either a
            string or bytes. It must remain secret and must be identical when
            calling ``unsign_state``.
        issued_at: Optional Unix timestamp in seconds. Normal application code
            should leave this as ``None`` so the current time is used. Supplying
            it explicitly is mainly useful for deterministic tests.

    Returns:
        A token in the form
        ``base64url(state).base64url(timestamp).hmac_signature``.

    Raises:
        ValueError: If ``state`` or ``secret_key`` is empty.
    """
    if not state:
        raise ValueError("state must not be empty")

    timestamp = str(int(time.time()) if issued_at is None else issued_at)
    payload = f"{_b64encode(state)}.{_b64encode(timestamp)}"
    signature = hmac.new(
        _secret_bytes(secret_key),
        payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def unsign_state(
    signed: str,
    secret_key: Secret,
    *,
    max_age: int,
    current_time: int | None = None,
    clock_skew: int = 30,
) -> str:
    """Verify and decode a signed OAuth state token.

    Args:
        signed: The complete token returned by ``sign_state``.
        secret_key: The same private HMAC key that was used to create the token.
        max_age: Maximum token lifetime in seconds. For example, ``600`` makes
            the state valid for ten minutes. It must be greater than zero.
        current_time: Optional Unix timestamp in seconds used as the verification
            time. Leave it as ``None`` in application code. Supplying a value is
            mainly useful for deterministic expiration tests.
        clock_skew: Number of seconds a token timestamp may be ahead of the
            verifier's clock. This accommodates small clock differences between
            servers. The default is 30 seconds.

    Returns:
        The original, decoded OAuth state value.

    Raises:
        ValueError: If the token is malformed, has been modified, is expired,
            has an unacceptable future timestamp, or the arguments are invalid.

    Security:
        The signature comparison uses ``hmac.compare_digest`` to reduce timing
        side channels. A valid signature proves integrity, not confidentiality;
        the state value is encoded but is not encrypted.
    """
    if max_age <= 0:
        raise ValueError("max_age must be greater than zero")

    try:
        state_b64, timestamp_b64, signature = signed.split(".")
        # Base64url components and the separator are guaranteed to be ASCII.
        payload = f"{state_b64}.{timestamp_b64}"
        expected = hmac.new(
            _secret_bytes(secret_key),
            payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError

        issued_at = int(_b64decode(timestamp_b64))
        now = int(time.time()) if current_time is None else current_time
        age = now - issued_at

        if age < -clock_skew or age > max_age:
            raise ValueError

        return _b64decode(state_b64)
    except (TypeError, ValueError, UnicodeDecodeError):
        raise ValueError("invalid or expired state") from None
