"""Unit tests for srf.tools.signing."""

import pytest

from srf.tools.signing import sign_state, unsign_state


SECRET = "test-secret-key"


class TestSignState:
    def test_round_trip(self):
        signed = sign_state("abc123", SECRET, issued_at=1_700_000_000)
        assert unsign_state(signed, SECRET, max_age=600, current_time=1_700_000_100) == "abc123"

    def test_unicode_state(self):
        signed = sign_state("状态值", SECRET, issued_at=1_700_000_000)
        assert unsign_state(signed, SECRET, max_age=600, current_time=1_700_000_000) == "状态值"

    def test_empty_state_raises(self):
        with pytest.raises(ValueError, match="state must not be empty"):
            sign_state("", SECRET)

    def test_empty_secret_raises(self):
        with pytest.raises(ValueError, match="secret_key must not be empty"):
            sign_state("state", "")

    def test_bytes_secret(self):
        signed = sign_state("state", b"bytes-secret", issued_at=100)
        assert unsign_state(signed, b"bytes-secret", max_age=10, current_time=105) == "state"


class TestUnsignState:
    def test_tampered_signature_raises(self):
        signed = sign_state("state", SECRET, issued_at=100)
        parts = signed.split(".")
        parts[-1] = "0" * len(parts[-1])
        with pytest.raises(ValueError, match="invalid or expired state"):
            unsign_state(".".join(parts), SECRET, max_age=600, current_time=100)

    def test_expired_raises(self):
        signed = sign_state("state", SECRET, issued_at=100)
        with pytest.raises(ValueError, match="invalid or expired state"):
            unsign_state(signed, SECRET, max_age=10, current_time=120)

    def test_future_beyond_clock_skew_raises(self):
        signed = sign_state("state", SECRET, issued_at=200)
        with pytest.raises(ValueError, match="invalid or expired state"):
            unsign_state(signed, SECRET, max_age=600, current_time=100, clock_skew=30)

    def test_within_clock_skew_ok(self):
        signed = sign_state("state", SECRET, issued_at=110)
        assert unsign_state(signed, SECRET, max_age=600, current_time=100, clock_skew=30) == "state"

    def test_max_age_must_be_positive(self):
        signed = sign_state("state", SECRET, issued_at=100)
        with pytest.raises(ValueError, match="max_age must be greater than zero"):
            unsign_state(signed, SECRET, max_age=0, current_time=100)

    def test_malformed_token_raises(self):
        with pytest.raises(ValueError, match="invalid or expired state"):
            unsign_state("not-a-token", SECRET, max_age=600, current_time=100)

    def test_wrong_secret_raises(self):
        signed = sign_state("state", SECRET, issued_at=100)
        with pytest.raises(ValueError, match="invalid or expired state"):
            unsign_state(signed, "other-secret", max_age=600, current_time=100)
