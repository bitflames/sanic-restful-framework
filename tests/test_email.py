"""Unit tests for email delivery and email verification endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sanic.exceptions import BadRequest, ServerError

from srf.tools.email import EmailCodeVerifySchema, EmailValidator, send_email, send_template_email
from srf.views.http_status import HTTPStatus


class TestEmailSchemas:
    def test_valid_email_and_six_digit_code(self):
        schema = EmailCodeVerifySchema(email="User@example.com", confirmations="001234")
        assert schema.email == "User@example.com"
        assert schema.confirmations == "001234"

    @pytest.mark.parametrize("email", ["invalid", "missing-domain@", "@example.com"])
    def test_rejects_invalid_email(self, email):
        with pytest.raises(ValidationError):
            EmailValidator(email=email)

    @pytest.mark.parametrize("code", ["12345", "1234567", "12ab56"])
    def test_rejects_invalid_verification_code(self, code):
        with pytest.raises(ValidationError):
            EmailCodeVerifySchema(email="user@example.com", confirmations=code)


class TestSendEmail:
    def test_sends_using_starttls(self):
        server = MagicMock()
        with patch("srf.tools.email.EmailConfig") as config, patch("srf.tools.email.smtplib.SMTP") as smtp:
            config.from_email = "from@example.com"
            config.smtp_server = "smtp.example.com"
            config.smtp_port = "587"
            config.password = "secret"
            smtp.return_value = server

            assert send_email("to@example.com", "subject", "body") is True

        server.starttls.assert_called_once()
        server.login.assert_called_once_with("from@example.com", "secret")
        server.sendmail.assert_called_once()
        server.quit.assert_called_once()

    def test_uses_ssl_on_port_465(self):
        server = MagicMock()
        with patch("srf.tools.email.EmailConfig") as config, patch("srf.tools.email.smtplib.SMTP_SSL") as smtp_ssl:
            config.from_email = "from@example.com"
            config.smtp_server = "smtp.example.com"
            config.smtp_port = "465"
            config.password = "secret"
            smtp_ssl.return_value = server

            assert send_email("to@example.com", "subject", "body") is True

        smtp_ssl.assert_called_once()
        server.starttls.assert_not_called()

    def test_returns_false_on_smtp_error_and_closes_connection(self):
        server = MagicMock()
        server.login.side_effect = OSError("connection failed")
        with patch("srf.tools.email.EmailConfig") as config, patch("srf.tools.email.smtplib.SMTP") as smtp:
            config.from_email = "from@example.com"
            config.smtp_server = "smtp.example.com"
            config.smtp_port = "587"
            config.password = "secret"
            smtp.return_value = server

            assert send_email("to@example.com", "subject", "body") is False

        server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_email_renders_then_offloads_smtp(self):
        with patch("srf.tools.email.asyncio.to_thread", new_callable=AsyncMock, return_value=True) as to_thread:
            result = await send_template_email("to@example.com", "subject", "email_code.html", {"code": "001234", "duration": "60s"})
        assert result is True
        args = to_thread.await_args.args
        assert args[0] is send_email
        assert args[1:3] == ("to@example.com", "subject")
        assert "001234" in args[3]


def make_request(json_body=None, redis=None, auth=None):
    request = MagicMock()
    request.json = json_body
    request.app.ctx.redis = redis if redis is not None else AsyncMock()
    request.app.ctx.auth = auth
    return request


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_requires_json_body(self):
        from srf.auth.viewset import verify_email

        with pytest.raises(BadRequest, match="JSON request body is required"):
            await verify_email(make_request())

    @pytest.mark.asyncio
    async def test_stores_code_atomically_and_sends_template(self):
        from srf.auth.viewset import verify_email

        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=1)
        request = make_request({"email": "USER@example.com"}, redis)
        with (
            patch("srf.auth.viewset.generate_code", return_value="001234"),
            patch("srf.auth.viewset.send_template_email", new_callable=AsyncMock, return_value=True) as send,
        ):
            response = await verify_email(request)

        assert response.status == HTTPStatus.HTTP_200_OK
        args = redis.eval.await_args.args
        assert args[0]  # Lua script
        assert args[1:4] == (2, "USER_REGISTER:EMAIL_CODE:user@example.com", "USER_REGISTER:EMAIL_CODE_TIMES:user@example.com")
        assert args[4:] == ("001234", 60)
        send.assert_awaited_once()
        assert send.await_args.kwargs["to_email"] == "user@example.com"
        assert send.await_args.kwargs["context"]["code"] == "001234"

    @pytest.mark.asyncio
    async def test_existing_code_is_rate_limited(self):
        from srf.auth.viewset import verify_email

        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=0)
        with patch("srf.auth.viewset.send_template_email", new_callable=AsyncMock) as send:
            response = await verify_email(make_request({"email": "user@example.com"}, redis))
        assert response.status == HTTPStatus.HTTP_429_TOO_MANY_REQUESTS
        send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_failure_removes_only_its_code_and_raises_server_error(self):
        from srf.auth.viewset import verify_email

        redis = AsyncMock()
        redis.eval = AsyncMock(side_effect=[1, 1])
        request = make_request({"email": "user@example.com"}, redis)
        with (
            patch("srf.auth.viewset.generate_code", return_value="001234"),
            patch("srf.auth.viewset.send_template_email", new_callable=AsyncMock, return_value=False),
            pytest.raises(ServerError),
        ):
            await verify_email(request)
        assert redis.eval.await_count == 2


class TestRegisterEmailCode:
    @pytest.mark.asyncio
    async def test_requires_json_body(self):
        from srf.auth.viewset import register

        with pytest.raises(BadRequest):
            await register(make_request())

    @pytest.mark.asyncio
    async def test_invalid_code_returns_bad_request(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=0)
        request = make_request(
            {"email": "user@example.com", "confirmations": "123456", "username": "alice", "password1": "Secret123", "password2": "Secret123"},
            redis,
        )
        with pytest.raises(BadRequest, match="invalid or has expired"):
            await register(request)

    @pytest.mark.asyncio
    async def test_valid_code_creates_user_and_returns_tokens(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=1)
        request = make_request(
            {"email": "user@example.com", "confirmations": "001234", "username": "alice", "password1": "Secret123", "password2": "Secret123"},
            redis,
        )
        user = MagicMock(id=7)
        token_payload = {"id": 7, "username": "alice", "access_token": "access", "refresh_token": "refresh"}
        with (
            patch("srf.auth.viewset.models.User.create_user", new_callable=AsyncMock, return_value=user) as create_user,
            patch("srf.auth.viewset.update_user_last_login", new_callable=AsyncMock) as update_last_login,
            patch("srf.auth.viewset.gen_user_access_token", new_callable=AsyncMock, return_value=token_payload),
        ):
            response = await register(request)

        assert response.status == HTTPStatus.HTTP_200_OK
        assert json.loads(response.body) == token_payload
        create_user.assert_awaited_once()
        assert create_user.await_args.args[0]["email"] == "user@example.com"
        assert create_user.await_args.args[0]["password"] == "Secret123"
        update_last_login.assert_awaited_once_with(user)
        assert redis.eval.await_args.args[1:4] == (
            2,
            "USER_REGISTER:EMAIL_CODE:user@example.com",
            "USER_REGISTER:EMAIL_CODE_TIMES:user@example.com",
        )

    @pytest.mark.asyncio
    async def test_wrong_code_increments_attempts_and_eventually_locks_out(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=2)
        request = make_request(
            {"email": "user@example.com", "confirmations": "123456", "username": "alice", "password1": "Secret123", "password2": "Secret123"},
            redis,
        )
        with pytest.raises(BadRequest, match="verification code is invalid"):
            await register(request)
