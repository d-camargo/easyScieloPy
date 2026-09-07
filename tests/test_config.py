import warnings

import pytest

from easyscielo.config import (
    _WARNED_SOURCES,
    crossref_mailto,
    openalex_api_key,
    openalex_email,
    redact,
    warn_no_contact,
)


@pytest.mark.parametrize(
    "func,env_name",
    [
        (openalex_email, "OPENALEX_EMAIL"),
        (openalex_api_key, "OPENALEX_API_KEY"),
        (crossref_mailto, "CROSSREF_MAILTO"),
    ],
)
def test_config_precedence(monkeypatch, func, env_name):
    # 1. Argument explicit takes precedence over env and None
    monkeypatch.setenv(env_name, "env_value@test.com")
    assert func("explicit_value@test.com") == "explicit_value@test.com"

    # 2. Env variable takes precedence when explicit argument is None
    assert func() == "env_value@test.com"
    assert func(None) == "env_value@test.com"

    # 3. None returned when explicit is None and env variable is deleted
    monkeypatch.delenv(env_name, raising=False)
    assert func() is None
    assert func(None) is None


def test_redact_empty_and_short_secrets():
    assert redact(None) == "***"
    assert redact("") == "***"
    assert redact("short") == "***"
    assert redact("12345678") == "***"


def test_redact_long_secrets():
    assert redact("abcdefghijklmnopqrstuvwxyz") == "abcd…wxyz"
    assert redact("123456789") == "1234…6789"


def test_redact_never_returns_full_secret():
    secrets = [
        "",
        "a",
        "secret",
        "12345678",
        "123456789",
        "my-secret-api-key-12345",
        "abcdefghijklmnopqrstuvwxyz",
    ]
    for secret in secrets:
        redacted = redact(secret)
        if secret:
            assert redacted != secret, f"Secret {secret!r} was returned unredacted!"


def test_warn_no_contact_emits_once(monkeypatch):
    # Reset warned sources state for deterministic testing
    _WARNED_SOURCES.clear()

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")

        # First call should emit a warning
        warn_no_contact("OpenAlex")
        assert len(record) == 1
        assert issubclass(record[0].category, UserWarning)
        msg = str(record[0].message)
        assert "sem e-mail" in msg.lower()
        assert "pool comum" in msg.lower()

        # Second call should not emit another warning
        warn_no_contact("OpenAlex")
        assert len(record) == 1
