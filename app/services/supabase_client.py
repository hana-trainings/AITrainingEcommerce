"""Creates the Supabase client. Only files in app/services may import this.

Why one client PER BROWSER SESSION (stored in st.session_state) and not one
shared client (st.cache_resource)?
After sign-in the client holds that user's access token. A shared client would
let user B make requests with user A's token. So every session gets its own
client, and Row Level Security in the database sees the right user.

Public, non-user data (the catalog) can still be cached with st.cache_data in
catalog.py; caching the DATA is fine, sharing the signed-in CLIENT is not.
"""

import streamlit as st

from app.config.settings import get_settings
from supabase import Client, ClientOptions, create_client

# Session-state key that holds this browser session's client.
# Tests put a fake client under this key (see tests/conftest.py).
CLIENT_SESSION_KEY = "supabase_client"


def _new_client() -> Client:
    settings = get_settings()
    options = ClientOptions(
        # Token refresh is a story of its own (U3-15, NFR-AUTH-04) and will be
        # handled by auth.refresh_session(); no background refresh thread for now.
        auto_refresh_token=False,
        # The session lives only in this client's memory (inside st.session_state),
        # never on disk (NFR-AUTH-03).
        persist_session=False,
    )
    return create_client(settings.supabase_url, settings.supabase_publishable_key, options=options)


def get_client() -> Client:
    """Return this browser session's Supabase client, creating it the first time."""
    if CLIENT_SESSION_KEY not in st.session_state:
        st.session_state[CLIENT_SESSION_KEY] = _new_client()
    return st.session_state[CLIENT_SESSION_KEY]


def reset_client() -> None:
    """Forget this session's client (used on sign-out). The next call makes a fresh one."""
    if CLIENT_SESSION_KEY in st.session_state:
        del st.session_state[CLIENT_SESSION_KEY]
