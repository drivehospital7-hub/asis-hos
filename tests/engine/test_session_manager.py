"""Unit tests for SessionManager — context manager + savepoints."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestSessionManagerEnterExit:
    """Tests for SessionManager.__enter__ and __exit__."""

    def test_import_exists(self):
        from app.services.engine.session_manager import SessionManager

        assert SessionManager is not None

    @patch("app.services.engine.session_manager.get_session")
    def test_enter_yields_session_manager(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with SessionManager("odontologia") as mgr:
            assert isinstance(mgr, SessionManager)
            assert mgr._session is mock_session

        mock_get_session.assert_called_once()

    @patch("app.services.engine.session_manager.get_session")
    def test_exit_calls_commit_on_success(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with SessionManager("odontologia"):
            pass

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("app.services.engine.session_manager.get_session")
    def test_exit_calls_rollback_on_exception(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError):
            with SessionManager("odontologia"):
                raise RuntimeError("test error")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("app.services.engine.session_manager.get_session")
    def test_stores_domain_name(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        sm = SessionManager("urgencias")
        with sm:
            pass

        assert sm._domain == "urgencias"


class TestSessionManagerSavepoint:
    """Tests for SessionManager.savepoint() — nested transactions."""

    @patch("app.services.engine.session_manager.get_session")
    def test_savepoint_creates_nested_transaction(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with SessionManager("odontologia") as session:
            with session.savepoint():
                pass

        mock_session.begin_nested.assert_called_once()

    @patch("app.services.engine.session_manager.get_session")
    def test_savepoint_rollback_does_not_kill_outer_session(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with SessionManager("odontologia") as session:
            with pytest.raises(ValueError):
                with session.savepoint():
                    raise ValueError("savepoint error")

        # Outer session commit should still work after savepoint rollback
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @patch("app.services.engine.session_manager.get_session")
    def test_savepoint_commit_on_success(self, mock_get_session):
        from app.services.engine.session_manager import SessionManager

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with SessionManager("odontologia") as session:
            with session.savepoint():
                session.add("dummy")

        # begin_nested was called
        mock_session.begin_nested.assert_called_once()
        # Outer commit still happens
        mock_session.commit.assert_called_once()
