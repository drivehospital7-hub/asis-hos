"""Tests for the Rate Limiter layer (PR 2).

Verifies:
- @rate_limit decorator blocks N+1 POST requests within window with 429
- GET requests are excluded from counting
- 429 response includes "Demasiadas solicitudes" with wait seconds
- Window expiry prunes old timestamps and allows new requests
- Session isolation — independent sessions have independent counters
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from flask import Flask, jsonify


class TestRateLimitDecorator:
    """Tests for the rate_limit decorator using a test Flask app.

    Creates ephemeral test routes with @rate_limit to verify the decorator
    behavior without coupling to the real application routes.
    """

    @pytest.fixture
    def app(self):
        """Creates a Flask app with rate-limited test routes."""
        app_ = Flask(__name__)
        app_.secret_key = "test-secret-key"
        app_.config["TESTING"] = True

        from app.services.processor_gate import rate_limit

        @app_.route("/test-post", methods=["POST"])
        @rate_limit(limit=3, window=60)
        def test_post():
            return jsonify({"status": "success"}), 200

        @app_.route("/test-get", methods=["GET"])
        @rate_limit(limit=3, window=60)
        def test_get():
            return jsonify({"status": "success"}), 200

        return app_

    # =========================================================================
    # Task 3.1 RED: N+1 requests within window → 429
    # =========================================================================

    def test_rate_limit_blocks_at_n_plus_1(self, app):
        """RED: N+1 POST requests within window → 429."""
        with app.test_client() as client:
            # N requests (limit=3) should pass
            for i in range(3):
                resp = client.post("/test-post")
                assert resp.status_code == 200, (
                    f"Request {i + 1} should be 200, got {resp.status_code}"
                )

            # N+1th request should be 429
            resp = client.post("/test-post")
            assert resp.status_code == 429, (
                f"N+1 request should be 429, got {resp.status_code}"
            )
            data = resp.get_json()
            assert data is not None
            assert "errors" in data
            assert any("Demasiadas solicitudes" in e for e in data["errors"]), (
                f"Error should contain 'Demasiadas solicitudes': {data['errors']}"
            )

    def test_rate_limit_allows_within_limit(self, app):
        """TRIANGULATE: Up to N POST requests should all pass."""
        with app.test_client() as client:
            for i in range(3):
                resp = client.post("/test-post")
                assert resp.status_code == 200, (
                    f"Request {i + 1} (within limit) should be 200, got {resp.status_code}"
                )

    def test_rate_limit_message_includes_seconds(self, app):
        """TRIANGULATE: 429 response must include wait seconds in message."""
        with app.test_client() as client:
            for _ in range(3):
                client.post("/test-post")

            resp = client.post("/test-post")
            assert resp.status_code == 429
            data = resp.get_json()
            assert data is not None
            error_msg = data["errors"][0]
            assert "segundos" in error_msg, (
                f"Error should mention 'segundos': {error_msg}"
            )
            # Extract the number of seconds
            import re
            seconds_match = re.search(r"(\d+)", error_msg)
            assert seconds_match is not None, (
                f"Error should include a number of seconds: {error_msg}"
            )
            seconds = int(seconds_match.group(1))
            assert seconds >= 1, f"Wait seconds should be at least 1, got {seconds}"

    # =========================================================================
    # Triangulation: GET requests are NOT counted
    # =========================================================================

    def test_get_requests_not_counted(self, app):
        """TRIANGULATE: GET requests must not affect rate limit counting."""
        with app.test_client() as client:
            # Send many GET requests — none should trigger rate limit
            for i in range(10):
                resp = client.get("/test-get")
                assert resp.status_code == 200, (
                    f"GET request {i + 1} should be 200, got {resp.status_code}"
                )

    def test_get_after_post_limit_still_works(self, app):
        """TRIANGULATE: GET still works even after POST limit is exceeded."""
        with app.test_client() as client:
            # Exhaust POST limit
            for _ in range(3):
                client.post("/test-post")

            # POST should be blocked
            resp = client.post("/test-post")
            assert resp.status_code == 429

            # GET should still work
            resp = client.get("/test-get")
            assert resp.status_code == 200, (
                f"GET after POST limit exceeded should be 200, got {resp.status_code}"
            )

    # =========================================================================
    # Task 3.3 RED: Window expiry — N+1th after >window seconds → 200
    # =========================================================================

    def test_window_expiry_prunes_and_allows(self, app):
        """RED: After window + 1s, old timestamps pruned → new request passes."""
        base_time = 1000000.0

        with patch("time.time") as mock_time:
            mock_time.return_value = base_time

            with app.test_client() as client:
                # Exhaust limit with 3 requests at base_time
                for _ in range(3):
                    resp = client.post("/test-post")
                    assert resp.status_code == 200

                # 4th request at base_time should be 429
                resp = client.post("/test-post")
                assert resp.status_code == 429

                # Now advance time past the 60s window
                mock_time.return_value = base_time + 61.0

                # 5th request: old timestamps should be pruned
                resp = client.post("/test-post")
                assert resp.status_code == 200, (
                    f"After window expiry, request should be 200, got {resp.status_code}"
                )

    def test_partial_window_still_blocks(self, app):
        """TRIANGULATE: Within window but not expired → still blocked."""
        base_time = 1000000.0

        with patch("time.time") as mock_time:
            mock_time.return_value = base_time

            with app.test_client() as client:
                for _ in range(3):
                    resp = client.post("/test-post")
                    assert resp.status_code == 200

                # Advance time only 30s — still within the 60s window
                mock_time.return_value = base_time + 30.0

                # Should still be blocked — old timestamps are valid
                resp = client.post("/test-post")
                assert resp.status_code == 429, (
                    f"Within window should still be 429, got {resp.status_code}"
                )

    # =========================================================================
    # Task 3.7 REFACTOR: Session isolation
    # =========================================================================

    def test_session_isolation(self, app):
        """REFACTOR: Two sessions should have independent rate limit counters."""
        client_a = app.test_client()
        client_b = app.test_client()

        # Exhaust session A's limit
        for _ in range(3):
            resp = client_a.post("/test-post")
            assert resp.status_code == 200

        # Session A should now be blocked
        resp = client_a.post("/test-post")
        assert resp.status_code == 429

        # Session B should be unaffected (independent)
        resp = client_b.post("/test-post")
        assert resp.status_code == 200, (
            f"Session B should be independent, got {resp.status_code}"
        )

        # Session B can make up to 3 requests
        for i in range(2):
            resp = client_b.post("/test-post")
            assert resp.status_code == 200, (
                f"Session B request {i + 2} should be 200, got {resp.status_code}"
            )

        # Session B's 4th should be blocked
        resp = client_b.post("/test-post")
        assert resp.status_code == 429

    def test_session_isolation_different_blocked_states(self, app):
        """TRIANGULATE: Sessions can be at different points in the limit."""
        client_a = app.test_client()
        client_b = app.test_client()
        client_c = app.test_client()

        # Session A: 0 requests → should pass
        resp = client_a.post("/test-post")
        assert resp.status_code == 200

        # Session B: 1 request → should pass
        resp = client_b.post("/test-post")
        assert resp.status_code == 200
        resp = client_b.post("/test-post")
        assert resp.status_code == 200

        # Session C: exhaust all 3 → should be blocked on 4th
        for _ in range(3):
            resp = client_c.post("/test-post")
            assert resp.status_code == 200
        resp = client_c.post("/test-post")
        assert resp.status_code == 429

        # Session A still has capacity (only 1 used)
        resp = client_a.post("/test-post")
        assert resp.status_code == 200
        resp = client_a.post("/test-post")
        assert resp.status_code == 200

        # Session A's 4th should be blocked
        resp = client_a.post("/test-post")
        assert resp.status_code == 429

        # Session B has used 2 of 3
        resp = client_b.post("/test-post")
        assert resp.status_code == 200
        resp = client_b.post("/test-post")
        assert resp.status_code == 429
