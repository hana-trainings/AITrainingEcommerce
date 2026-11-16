"""Settings must fail fast and must refuse the secret key (NFR-SEC-08, NFR-SEC-12)."""

import pytest
import streamlit as st

from app.config import settings


@pytest.fixture
def no_secret_files(monkeypatch):
    """Ignore any real .env / secrets.toml on this machine; use only test env vars."""
    monkeypatch.setattr(settings, "load_dotenv", lambda **_kwargs: False)
    monkeypatch.setattr(st.secrets, "load_if_toml_exists", lambda: False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)


def test_missing_settings_are_named_but_not_printed(no_secret_files):
    with pytest.raises(settings.SettingsError) as error:
        settings.load_settings()
    assert "SUPABASE_URL" in str(error.value)
    assert "SUPABASE_PUBLISHABLE_KEY" in str(error.value)


def test_secret_key_is_refused(no_secret_files, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_secret_do_not_use")

    with pytest.raises(settings.SettingsError) as error:
        settings.load_settings()
    assert "sb_secret_do_not_use" not in str(error.value)  # never echo the value


def test_publishable_key_is_accepted(no_secret_files, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")

    loaded = settings.load_settings()
    assert loaded.supabase_publishable_key == "sb_publishable_test"
