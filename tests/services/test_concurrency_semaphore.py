"""Tests for the Concurrency Semaphore layer (PR 3, Phase 4).

Verifies:
- acquire_semaphore / release_semaphore under capacity → success
- acquire_semaphore at capacity → returns False (timeout)
- Flask route returns 503 when semaphore at capacity
- Exception safety — task raising releases semaphore in finally
- [BACK] logging at acquire/release
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, jsonify


# =============================================================================
# Task 4.1 RED: Under capacity → acquire/release success
# =============================================================================


class TestSemaphoreAcquireRelease:
    """Direct unit tests for acquire_semaphore and release_semaphore."""

    def test_acquire_semaphore_returns_true_under_capacity(self) -> None:
        """RED: Under capacity, acquire_semaphore must return True."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        try:
            result = acquire_semaphore(timeout=1)
            assert result is True, (
                f"Under capacity, acquire should return True, got {result}"
            )
        finally:
            release_semaphore()

    def test_acquire_release_cycle_maintains_count(self) -> None:
        """TRIANGULATE: Acquire then release should keep semaphore usable."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Acquire all 3 slots and release them one by one
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True, (
                    f"Acquire {i + 1} should be True, got {result}"
                )
                acquired.append(True)
        finally:
            for _ in acquired:
                release_semaphore()

        # After releasing all, should be able to acquire again
        try:
            result = acquire_semaphore(timeout=1)
            assert result is True, (
                f"After full release, acquire should return True, got {result}"
            )
        finally:
            release_semaphore()

    def test_release_without_acquire_does_not_raise(self) -> None:
        """TRIANGULATE: Calling release without acquire must not crash."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Releasing when semaphore is at full count should not error
        # (Semaphore.release() increments counter even if already at max)
        release_semaphore()  # Should not raise — now 4 permits
        # Re-acquire the extra permit to restore state to 3
        result = acquire_semaphore(timeout=1)
        assert result is True, "Should re-acquire extra permit to restore state"

    def test_acquire_with_zero_timeout_under_capacity(self) -> None:
        """TRIANGULATE: acquire with timeout=0 under capacity returns True."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        try:
            result = acquire_semaphore(timeout=0)
            assert result is True, (
                f"With timeout=0 under capacity, should return True, got {result}"
            )
        finally:
            release_semaphore()


# =============================================================================
# Task 4.3 RED: At capacity → acquire returns False
# =============================================================================


class TestSemaphoreAtCapacity:
    """Semaphore at capacity: acquire should return False."""

    def test_acquire_at_capacity_returns_false(self) -> None:
        """RED: With all 3 permits taken, acquire should return False."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Exhaust all 3 permits
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True, (
                    f"Acquire permit {i + 1} should be True, got {result}"
                )
                acquired.append(True)

            # 4th acquire with short timeout should fail
            result = acquire_semaphore(timeout=0.1)
            assert result is False, (
                "At capacity, acquire should return False, got True"
            )
        finally:
            for _ in acquired:
                release_semaphore()

    def test_acquire_at_capacity_then_release_allows_new(self) -> None:
        """TRIANGULATE: After one release, acquire should succeed again."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True
                acquired.append(True)

            # 4th should fail
            result = acquire_semaphore(timeout=0.1)
            assert result is False
        finally:
            for _ in acquired:
                release_semaphore()

        # After releasing one slot, should be able to acquire again
        try:
            result = acquire_semaphore(timeout=1)
            assert result is True, (
                "After one release at capacity, acquire should succeed"
            )
        finally:
            release_semaphore()

    def test_acquire_with_negative_timeout_under_capacity(self) -> None:
        """TRIANGULATE: Negative timeout under capacity should still work (blocking=False)."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        try:
            result = acquire_semaphore(timeout=-1)
            assert result is True, (
                f"Negative timeout under capacity returns True, got {result}"
            )
        finally:
            release_semaphore()


# =============================================================================
# Task 4.3 (Flask level): Route returns 503 when semaphore at capacity
# =============================================================================


class TestSemaphoreFlask503:
    """Flask route returns 503 when semaphore cannot be acquired."""

    @pytest.fixture
    def app(self):
        """Creates a Flask app with a test route that uses the semaphore."""
        app_ = Flask(__name__)
        app_.secret_key = "test-secret-key"
        app_.config["TESTING"] = True

        from app.services.processor_gate import (
            acquire_semaphore,
            release_semaphore,
        )

        @app_.route("/test-process", methods=["POST"])
        def test_process():
            if not acquire_semaphore(timeout=0.1):
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": [
                        "Servidor ocupado. Intente nuevamente en unos momentos."
                    ],
                }), 503
            try:
                return jsonify({"status": "success", "data": {}, "errors": []}), 200
            finally:
                release_semaphore()

        return app_

    def test_semaphore_under_capacity_returns_200(self, app) -> None:
        """RED: Under capacity, route returns 200."""
        with app.test_client() as client:
            resp = client.post("/test-process")
            assert resp.status_code == 200, (
                f"Under capacity should return 200, got {resp.status_code}"
            )
            data = resp.get_json()
            assert data is not None
            assert data["status"] == "success"

    def test_semaphore_at_capacity_returns_503(self, app) -> None:
        """RED: At capacity, route returns 503."""
        from app.services.processor_gate import (
            acquire_semaphore,
            release_semaphore,
        )

        # Exhaust the real semaphore — apply to the same module
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True
                acquired.append(True)

            # Now Flask route should return 503
            with app.test_client() as client:
                resp = client.post("/test-process")
                assert resp.status_code == 503, (
                    f"At capacity should return 503, got {resp.status_code}"
                )
                data = resp.get_json()
                assert data is not None
                assert any(
                    "Servidor ocupado" in e for e in data.get("errors", [])
                ), f"503 error should mention 'Servidor ocupado': {data.get('errors')}"
        finally:
            for _ in acquired:
                release_semaphore()

    def test_semaphore_recovers_after_release(self, app) -> None:
        """TRIANGULATE: After a task completes, next request gets 200."""
        from app.services.processor_gate import (
            acquire_semaphore,
            release_semaphore,
        )

        # Exhaust 3 permits
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True
                acquired.append(True)
        finally:
            pass  # Keep holding

        # Release one
        release_semaphore()

        # Now the route should work (1 slot free)
        with app.test_client() as client:
            resp = client.post("/test-process")
            assert resp.status_code == 200, (
                f"After one release, should return 200, got {resp.status_code}"
            )
            # The test_route consumed the slot, release it
            # (acquire was done inside the route, release in its finally)

        # Clean up remaining acquired permits
        for _ in acquired[:2]:
            release_semaphore()


# =============================================================================
# Task 4.5 RED: Exception safety — task raising releases semaphore
# =============================================================================


class TestSemaphoreExceptionSafety:
    """Exception safety: semaphore must be released even if task raises."""

    def test_exception_releases_semaphore(self) -> None:
        """RED: When processing raises, semaphore is released in finally."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        acquired_count = 0
        try:
            result = acquire_semaphore(timeout=1)
            assert result is True
            acquired_count += 1

            # Simulate a task that raises
            raise RuntimeError("Simulated processing error")
        except RuntimeError:
            pass  # Expected
        finally:
            # This is what we're testing: even with an exception, release happens
            release_semaphore()

        # Now we should be able to acquire again (semaphore was released)
        try:
            result = acquire_semaphore(timeout=1)
            assert result is True, (
                f"After exception release, acquire should succeed, got {result}"
            )
        finally:
            release_semaphore()

    def test_exception_in_flask_route_releases_semaphore(self, app_raising) -> None:
        """TRIANGULATE: Flask route with exception releases semaphore."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Call the raising route — it should crash but release semaphore
        with app_raising.test_client() as client:
            try:
                client.post("/test-raise")
            except RuntimeError:
                pass  # Expected

        # After the crash, semaphore should be released
        # There's one less permit now since the route acquired but the exception
        # handler in the route should have released it
        try:
            result = acquire_semaphore(timeout=1)
            assert result is True, (
                "After exception in Flask route, semaphore should be released"
            )
        finally:
            release_semaphore()

    @pytest.fixture
    def app_raising(self):
        """Creates a Flask app with a route that raises after acquiring semaphore."""
        app_ = Flask(__name__)
        app_.secret_key = "test-secret-key"
        app_.config["TESTING"] = True

        from app.services.processor_gate import (
            acquire_semaphore,
            release_semaphore,
        )

        @app_.route("/test-raise", methods=["POST"])
        def test_raise():
            if not acquire_semaphore(timeout=1):
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": ["Servidor ocupado"],
                }), 503
            try:
                raise RuntimeError("Simulated crash in processing")
            finally:
                release_semaphore()

        return app_


# =============================================================================
# Task 4.7 REFACTOR: [BACK] logging at semaphore acquire/release
# =============================================================================


class TestSemaphoreBackLogging:
    """[BACK] logging must appear at semaphore acquire and release."""

    def test_acquire_logs_back_prefix(self) -> None:
        """REFACTOR: acquire_semaphore must log with [BACK] prefix on success."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        with patch("app.services.processor_gate.logger") as mock_logger:
            try:
                result = acquire_semaphore(timeout=1)
                assert result is True
            finally:
                release_semaphore()

            # Verify [BACK] prefix appears in log
            mock_logger.info.assert_any_call(
                "[BACK] Semaphore acquired (running: %d/%d)",
                pytest.approx(1, abs=1),  # running count
                3,  # max concurrent
            )

    def test_release_logs_back_prefix(self) -> None:
        """REFACTOR: release_semaphore must log with [BACK] prefix."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        with patch("app.services.processor_gate.logger") as mock_logger:
            try:
                acquire_semaphore(timeout=1)
            finally:
                release_semaphore()

            # Find the release log call
            release_calls = [
                call for call in mock_logger.info.call_args_list
                if "[BACK] Semaphore released" in str(call)
            ]
            assert len(release_calls) >= 1, (
                "release_semaphore must log with [BACK] Semaphore released prefix"
            )

    def test_acquire_timeout_logs_back_prefix(self) -> None:
        """REFACTOR: acquire timeout must also log with [BACK] prefix."""
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Exhaust all permits
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True
                acquired.append(True)

            with patch("app.services.processor_gate.logger") as mock_logger:
                result = acquire_semaphore(timeout=0.1)
                assert result is False

                mock_logger.info.assert_any_call(
                    "[BACK] Semaphore timeout — all %d slots busy", 3
                )
        finally:
            for _ in acquired:
                release_semaphore()


# =============================================================================
# Issue 1 fix: detect_problems_only returns (dict, int) tuple
# =============================================================================


class TestDetectProblemsOnlyTupleReturn:
    """detect_problems_only must return (dict, status_code) tuple."""

    def test_returns_503_tuple_on_semaphore_timeout(self) -> None:
        """Detect_problems_only returns (error_dict, 503) when semaphore times out."""
        from app.services.exporter import detect_problems_only
        from app.services.processor_gate import acquire_semaphore, release_semaphore

        # Exhaust all 3 permits
        acquired = []
        try:
            for i in range(3):
                result = acquire_semaphore(timeout=1)
                assert result is True
                acquired.append(True)

            with patch("app.services.exporter.SEMAPHORE_TIMEOUT", 0.1):
                result, status_code = detect_problems_only(
                    filename="dummy.xlsx",
                    area="odontologia",
                )

            assert status_code == 503, (
                f"Expected 503 on semaphore timeout, got {status_code}"
            )
            assert result["status"] == "error"
            assert any(
                "Servidor ocupado" in e for e in result.get("errors", [])
            ), "503 error dict should contain 'Servidor ocupado'"
        finally:
            for _ in acquired:
                release_semaphore()

    def test_returns_200_tuple_on_success(self) -> None:
        """Detect_problems_only returns (result_dict, 200) when semaphore acquired."""
        from app.services.exporter import detect_problems_only

        expected_result = {
            "status": "success",
            "data": {"problemas": {}, "responsables_map": {}},
            "errors": [],
        }

        with patch(
            "app.services.exporter._do_detect_problems",
            return_value=expected_result,
        ) as mock_detect:
            result, status_code = detect_problems_only(
                filename="test.xlsx",
                area="odontologia",
            )

        assert status_code == 200, (
            f"Expected 200 on success, got {status_code}"
        )
        assert result == expected_result
        mock_detect.assert_called_once()

    def test_returns_500_tuple_on_exception(self) -> None:
        """Detect_problems_only returns (error_dict, 500) when processing raises."""
        from app.services.exporter import detect_problems_only

        with patch(
            "app.services.exporter._do_detect_problems",
            side_effect=RuntimeError("Procesamiento falló"),
        ):
            result, status_code = detect_problems_only(
                filename="test.xlsx",
                area="odontologia",
            )

        assert status_code == 500, (
            f"Expected 500 on exception, got {status_code}"
        )
        assert result["status"] == "error"
        assert any(
            "Error interno" in e for e in result.get("errors", [])
        ), "500 error dict should mention internal error"


