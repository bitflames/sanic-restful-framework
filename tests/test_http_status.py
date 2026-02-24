"""Unit tests for srf.views.http_status."""

import pytest

from srf.views.http_status import (
    HTTPStatus,
    is_client_error,
    is_informational,
    is_redirect,
    is_server_error,
    is_success,
)


class TestHTTPStatus:
    def test_common_codes(self):
        assert HTTPStatus.HTTP_200_OK == 200
        assert HTTPStatus.HTTP_201_CREATED == 201
        assert HTTPStatus.HTTP_204_NO_CONTENT == 204
        assert HTTPStatus.HTTP_400_BAD_REQUEST == 400
        assert HTTPStatus.HTTP_401_UNAUTHORIZED == 401
        assert HTTPStatus.HTTP_404_NOT_FOUND == 404
        assert HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY == 422
        assert HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR == 500

    def test_int_enum_usage(self):
        assert int(HTTPStatus.HTTP_200_OK) == 200


class TestHelpers:
    def test_is_informational(self):
        assert is_informational(100) is True
        assert is_informational(199) is True
        assert is_informational(200) is False

    def test_is_success(self):
        assert is_success(200) is True
        assert is_success(299) is True
        assert is_success(300) is False

    def test_is_redirect(self):
        assert is_redirect(302) is True
        assert is_redirect(200) is False

    def test_is_client_error(self):
        assert is_client_error(400) is True
        assert is_client_error(404) is True
        assert is_client_error(500) is False

    def test_is_server_error(self):
        assert is_server_error(500) is True
        assert is_server_error(400) is False
