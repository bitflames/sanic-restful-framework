"""Unit tests for srf.tools.utils."""

import re
import pytest

from srf.tools.utils import camel_to_snake, generate_code


class TestCamelToSnake:
    def test_simple(self):
        assert camel_to_snake("FooBar") == "foo_bar"

    def test_single_word(self):
        assert camel_to_snake("foo") == "foo"

    def test_multiple_caps(self):
        # Implementation converts to lowercase with underscores at word boundaries
        assert camel_to_snake("HTTPResponse") == "http_response"

    def test_mixed(self):
        assert camel_to_snake("getUserById") == "get_user_by_id"


class TestGenerateCode:
    def test_default_length(self):
        code = generate_code()
        assert len(code) == 5
        assert code.isdigit()

    def test_custom_length(self):
        code = generate_code(6)
        assert len(code) == 6
        assert code.isdigit()

    def test_different_each_time(self):
        codes = {generate_code(10) for _ in range(50)}
        assert len(codes) == 50
