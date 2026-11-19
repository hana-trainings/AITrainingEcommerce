"""App settings: where the Supabase URL and publishable key come from.

Order of lookup (first match wins):
1. `.streamlit/secrets.toml` locally, or the Secrets box on Streamlit Cloud
2. `.env` file in the repo root (loaded with python-dotenv) or real environment variables

The values are NEVER printed or logged. If something is missing, the app stops
with a message that names the missing setting, not its value (NFR-SEC-12).
"""

import os
from dataclasses import dataclass

import streamlit as st
from dotenv import load_dotenv

REQUIRED_SETTINGS = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")

# The secret key bypasses every security rule (RLS). It must never be used by the app.
FORBIDDEN_KEY_PREFIX = "sb_secret_"


class SettingsError(Exception):
    """Raised when settings are missing or unsafe. The message never contains a value."""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str


def _read_value(name: str) -> str:
    """Return one setting from st.secrets or the environment, or "" if not set."""
    # load_if_toml_exists() returns False instead of raising when there is no secrets file.
    if st.secrets.load_if_toml_exists():
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    return os.environ.get(name, "").strip()


def load_settings() -> Settings:
    """Read and check the settings. Raises SettingsError if anything is wrong."""
    load_dotenv(override=False)  # never overwrite real environment variables

    values = {name: _read_value(name) for name in REQUIRED_SETTINGS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SettingsError(
            "Missing setting(s): " + ", ".join(missing) + ". "
            "Copy .env.example to .env (or .streamlit/secrets.toml.example to "
            ".streamlit/secrets.toml) and fill them in."
        )

    if values["SUPABASE_PUBLISHABLE_KEY"].startswith(FORBIDDEN_KEY_PREFIX):
        raise SettingsError(
            "SUPABASE_PUBLISHABLE_KEY holds a SECRET key (sb_secret_...). "
            "The app must only use the publishable key (sb_publishable_...). "
            "Replace it, and never commit or share the secret key."
        )

    return Settings(
        supabase_url=values["SUPABASE_URL"],
        supabase_publishable_key=values["SUPABASE_PUBLISHABLE_KEY"],
    )


def get_settings() -> Settings:
    """Return settings for the running app, or stop the page with a clear message."""
    try:
        return load_settings()
    except SettingsError as error:
        st.error(str(error), title="The app is not configured yet", icon=":material/settings:")
        st.stop()
        raise  # st.stop() ends the script; this line only keeps type checkers happy
