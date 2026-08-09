"""Unit tests for srf.tools.email and auth email verification flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sanic.exceptions import BadRequest

from srf.config import settings
from srf.tools.email import EmailCodeVerifySchema, EmailValidator, send_email, send_verify_code
from srf.views.http_status import HTTPStatus


class TestEmailValidator:
    def test_valid_email(self):
        sch = EmailValidator(email="user@example.com")
        assert sch.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            EmailValidator(email="not-an-email")


class TestEmailCodeVerifySchema:
    def test_valid_code(self):
        sch = EmailCodeVerifySchema(email="u@example.com", confirmations="01234")
        assert sch.confirmations == "01234"

    def test_rejects_non_digit(self):
        with pytest.raises(ValidationError):
            EmailCodeVerifySchema(email="u@example.com", confirmations="12ab3")

    def test_rejects_wrong_length(self):
        with pytest.raises(ValidationError):
            EmailCodeVerifySchema(email="u@example.com", confirmations="1234")

    def test_keeps_leading_zeros(self):
        sch = EmailCodeVerifySchema(email="u@example.com", confirmations="00042")
        assert sch.confirmations == "00042"
        assert sch.confirmations != "42"


class TestSendEmail:
    def test_send_email_success(self):
        mock_server = MagicMock()
        with (
            patch("srf.tools.email.EmailConfig") as cfg,
            patch("srf.tools.email.smtplib.SMTP") as smtp_cls,
        ):
            cfg.from_email = "from@example.com"
            cfg.smtp_server = "smtp.example.com"
            cfg.smtp_port = "587"
            cfg.password = "secret"
            smtp_cls.return_value = mock_server

            assert send_email("to@example.com", "subj", "body") is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("from@example.com", "secret")
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

    def test_send_email_ssl_port(self):
        mock_server = MagicMock()
        with (
            patch("srf.tools.email.EmailConfig") as cfg,
            patch("srf.tools.email.smtplib.SMTP_SSL") as smtp_ssl,
        ):
            cfg.from_email = "from@example.com"
            cfg.smtp_server = "smtp.example.com"
            cfg.smtp_port = "465"
            cfg.password = "secret"
            smtp_ssl.return_value = mock_server

            assert send_email("to@example.com", "subj", "body") is True
            smtp_ssl.assert_called_once()
            mock_server.starttls.assert_not_called()

    def test_send_email_failure_returns_false(self):
        with (
            patch("srf.tools.email.EmailConfig") as cfg,
            patch("srf.tools.email.smtplib.SMTP") as smtp_cls,
        ):
            cfg.from_email = "from@example.com"
            cfg.smtp_server = "smtp.example.com"
            cfg.smtp_port = "587"
            cfg.password = "secret"
            mock_server = MagicMock()
            mock_server.login.side_effect = Exception("auth failed")
            smtp_cls.return_value = mock_server

            assert send_email("to@example.com", "subj", "body") is False
            mock_server.quit.assert_called_once()


class TestSendVerifyCode:
    @pytest.mark.asyncio
    async def test_runs_send_email_in_thread(self):
        with patch("srf.tools.email.send_email", return_value=True) as send_mock:
            ok = await send_verify_code("u@example.com", "12345")
            assert ok is True
            send_mock.assert_called_once()
            args = send_mock.call_args[0]
            assert args[0] == "u@example.com"
            assert "12345" in args[2]


def _make_request(json_body=None, redis=None):
    request = MagicMock()
    request.json = json_body
    request.app.ctx.redis = redis if redis is not None else AsyncMock()
    request.app.ctx.jwt = SimpleNamespace(config={})
    return request


class TestSendEmailWithRedisCode:
    @pytest.mark.asyncio
    async def test_requires_body(self):
        from srf.auth.viewset import send_email_with_redis_code

        request = _make_request(json_body=None)
        with pytest.raises(BadRequest, match="Request body is required"):
            await send_email_with_redis_code(request)

    @pytest.mark.asyncio
    async def test_rate_limits_when_code_exists(self):
        from srf.auth.viewset import send_email_with_redis_code

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"12345")
        request = _make_request(json_body={"email": "u@example.com"}, redis=redis)

        response = await send_email_with_redis_code(request)
        assert response.status == HTTPStatus.HTTP_429_TOO_MANY_REQUESTS
        redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_sets_redis_and_sends(self):
        from srf.auth.viewset import send_email_with_redis_code

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        request = _make_request(json_body={"email": "u@example.com"}, redis=redis)

        with (
            patch("srf.auth.viewset.generate_code", return_value="12345"),
            patch("srf.auth.viewset.send_verify_code", new_callable=AsyncMock, return_value=True) as send_mock,
        ):
            response = await send_email_with_redis_code(request)

        assert response.status == 200
        key = f"{settings.EMAIL_CODE_REDIS}_u@example.com"
        redis.set.assert_awaited_once_with(
            key,
            "12345",
            ex=settings.USER_REGISTER_EMAIL_VERIFY_CODE_TTL,
            nx=True,
        )
        send_mock.assert_awaited_once_with("u@example.com", "12345")
        redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_redis_when_send_fails(self):
        from srf.auth.viewset import send_email_with_redis_code

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock()
        request = _make_request(json_body={"email": "u@example.com"}, redis=redis)

        with (
            patch("srf.auth.viewset.generate_code", return_value="12345"),
            patch("srf.auth.viewset.send_verify_code", new_callable=AsyncMock, return_value=False),
        ):
            response = await send_email_with_redis_code(request)

        assert response.status == HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
        key = f"{settings.EMAIL_CODE_REDIS}_u@example.com"
        redis.delete.assert_awaited_once_with(key)


class TestRegisterEmailCode:
    @pytest.mark.asyncio
    async def test_requires_body(self):
        from srf.auth.viewset import register

        request = _make_request(json_body=None)
        with pytest.raises(BadRequest, match="Request body is required"):
            await register(request)

    @pytest.mark.asyncio
    async def test_wrong_code_returns_400_and_deletes(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"12345")
        redis.delete = AsyncMock()
        request = _make_request(
            json_body={"email": "u@example.com", "confirmations": "99999", "username": "alice", "password1": "x"},
            redis=redis,
        )

        response = await register(request)
        assert response.status == HTTPStatus.HTTP_400_BAD_REQUEST
        redis.delete.assert_awaited()

    @pytest.mark.asyncio
    async def test_missing_code_returns_400(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.delete = AsyncMock()
        request = _make_request(
            json_body={"email": "u@example.com", "confirmations": "12345", "username": "alice", "password1": "x"},
            redis=redis,
        )

        response = await register(request)
        assert response.status == HTTPStatus.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_success_creates_user_and_token(self):
        from srf.auth.viewset import register

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"12345")
        redis.delete = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "alice"
        mock_user.email = "u@example.com"
        mock_user.is_active = True
        mock_user.is_staff = False
        mock_user.is_superuser = False
        mock_user.last_login = None
        mock_user.date_joined = None
        mock_user.create_time = MagicMock()
        mock_user.update_time = MagicMock()
        mock_role = MagicMock()
        mock_role.name = "user"
        mock_user.role = mock_role

        request = _make_request(
            json_body={
                "email": "u@example.com",
                "confirmations": "12345",
                "username": "alice",
                "password1": "secret",
            },
            redis=redis,
        )

        auth_inst = AsyncMock()
        auth_inst.generate_access_token = AsyncMock(return_value="tok")

        with (
            patch("srf.auth.viewset.models.User.create", new_callable=AsyncMock, return_value=mock_user),
            patch("srf.auth.viewset.Authentication", return_value=auth_inst),
            patch("srf.auth.viewset.UserSchemaReader.model_validate") as reader_validate,
        ):
            reader_validate.return_value.model_dump.return_value = {
                "id": 1,
                "username": "alice",
                "email": "u@example.com",
            }
            response = await register(request)

        assert response.status == 200
        redis.delete.assert_awaited()
        auth_inst.generate_access_token.assert_awaited_once()
