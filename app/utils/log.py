"""Logging setup shared by the whole app (NFR-LOG-01).

Rules for every log line:
- Log what happened and where (page, action, user id).
- NEVER log passwords, tokens, keys, emails or display names.
"""

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a logger. Call it once per module: logger = get_logger(__name__)."""
    root = logging.getLogger()
    # Streamlit reruns scripts often; only add our handler the first time.
    if not any(getattr(h, "_skillforge", False) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        handler._skillforge = True  # type: ignore[attr-defined]
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return logging.getLogger(name)
