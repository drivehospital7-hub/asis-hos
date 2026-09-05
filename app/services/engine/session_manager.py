"""SessionManager — single DB session with savepoint support.

Eliminates per-rule DB session overhead by wrapping ``get_session()`` in a
context manager that yields a single session proxy for all rules in a domain.
Savepoints via ``session.begin_nested()`` preserve per-rule rollback
capability without closing the outer transaction.

Usage::

    with SessionManager("odontologia") as session:
        for rule in rules:
            with session.savepoint():
                engine.evaluate(...)
        # session.commit() called automatically on success
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

from app.database import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SessionManager:
    """Context manager providing a single DB session with savepoint support.

    Delegates attribute access (``commit``, ``rollback``, ``close``, ``add``,
    ``query``, etc.) to the underlying SQLAlchemy session while adding the
    ``savepoint()`` method for nested transaction control.
    """

    def __init__(self, domain: str) -> None:
        self._domain = domain
        self._session: Session | None = None

    def __enter__(self) -> SessionManager:
        self._session = get_session()
        logger.debug("Session opened for domain: %s", self._domain)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        assert self._session is not None
        if exc_type is None:
            self._session.commit()
            logger.debug("Session committed for domain: %s", self._domain)
        else:
            self._session.rollback()
            logger.warning(
                "Session rolled back for domain: %s due to %s",
                self._domain,
                exc_type.__name__,
            )
        self._session.close()
        logger.debug("Session closed for domain: %s", self._domain)

    @contextmanager
    def savepoint(self) -> Generator[None, None, None]:
        """Create a savepoint (nested transaction) within the current session.

        Allows per-rule rollback without affecting the outer transaction::

            with session.savepoint():
                engine.evaluate(...)  # rolled back on error, outer commit still valid
        """
        assert self._session is not None
        with self._session.begin_nested():
            yield

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the underlying session."""
        if self._session is None:
            msg = f"{type(self).__name__!r} has no session (not yet entered)"
            raise AttributeError(msg)
        return getattr(self._session, name)
