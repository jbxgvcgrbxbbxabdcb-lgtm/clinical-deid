"""Clinical De-identify FastAPI backend.

Run::

    uvicorn backend.app:app --host 127.0.0.1 --port 7870

Layout::

    routers/   HTTP routers
    services/  use-cases
    deid/      de-identify ops, rules, models
    store/     in-memory sessions / downloads
"""

from backend.app import app, create_app

__all__ = ["app", "create_app"]
