"""
Integration tests for moderation API endpoints.
Tests anonymous and authenticated content reporting.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import uuid


class TestModerationAPI:
    """Test suite for moderation API endpoints."""

    @pytest.fixture
    def mock_moderation_service(self):
        """Mock moderation service for testing."""
        with patch("api.v1.moderation.get_moderation_service") as mock:
            service = Mock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter for testing."""
        with patch("api.v1.moderation.report_rate_limiter") as mock:
            mock.is_rate_limited = AsyncMock(return_value=False)
            yield mock

    def test_report_content_anonymous_with_session_id(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test anonymous user can report content with session ID."""
        mock_moderation_service.report_content = AsyncMock(return_value=True)

        session_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "reason": "spam",
                "description": "This is spam",
            },
            headers={
                "X-User": "anonymous",
                "X-Session-Id": session_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reported successfully" in data["message"]

        # Verify service was called with session_id
        mock_moderation_service.report_content.assert_called_once()
        call_kwargs = mock_moderation_service.report_content.call_args.kwargs
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["user_id"] is None  # anonymous has no user_id

    def test_report_content_anonymous_without_session_id_fails(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test anonymous user without session ID gets validation error."""
        mock_moderation_service.report_content = AsyncMock(return_value=False)

        response = client.post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "reason": "spam",
            },
            headers={"X-User": "anonymous"},
            # No X-Session-Id header
        )

        assert response.status_code == 400
        assert "Failed to submit report" in response.json()["detail"]

    def test_report_content_authenticated_user(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test authenticated user can report content."""
        mock_moderation_service.report_content = AsyncMock(return_value=True)

        user_id = "test-user-123"
        response = client.post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "generictext",
                "reason": "inappropriate",
                "description": "Offensive content",
            },
            headers={"X-User": user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify service was called with user_id
        mock_moderation_service.report_content.assert_called_once()
        call_kwargs = mock_moderation_service.report_content.call_args.kwargs
        assert call_kwargs["user_id"] == user_id

    def test_report_content_rate_limiting(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test rate limiting prevents spam reporting."""
        mock_rate_limiter.is_rate_limited = AsyncMock(return_value=True)

        session_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "reason": "spam",
            },
            headers={
                "X-User": "anonymous",
                "X-Session-Id": session_id,
            },
        )

        assert response.status_code == 429
        assert "Too many reports" in response.json()["detail"]
        mock_moderation_service.report_content.assert_not_called()

    def test_report_content_valid_reasons(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test all valid report reasons are accepted."""
        mock_moderation_service.report_content = AsyncMock(return_value=True)

        valid_reasons = ["spam", "inappropriate", "duplicate", "other"]
        session_id = str(uuid.uuid4())

        for reason in valid_reasons:
            response = client.post(
                "/api/v1/moderation/report",
                json={
                    "content_id": str(uuid.uuid4()),
                    "content_type": "commentary",
                    "reason": reason,
                },
                headers={
                    "X-User": "anonymous",
                    "X-Session-Id": session_id,
                },
            )

            assert response.status_code == 200, f"Failed for reason: {reason}"

    def test_report_content_authenticated_user_prefers_user_id(
        self, client: TestClient, mock_moderation_service, mock_rate_limiter
    ):
        """Test authenticated user's user_id is preferred over session_id."""
        mock_moderation_service.report_content = AsyncMock(return_value=True)

        user_id = "test-user-123"
        session_id = str(uuid.uuid4())

        response = client.post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "reason": "spam",
            },
            headers={
                "X-User": user_id,
                "X-Session-Id": session_id,  # Also send session ID
            },
        )

        assert response.status_code == 200

        # Verify service was called with user_id, not session_id for rate limiting
        call_kwargs = mock_moderation_service.report_content.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        # Session ID still passed but user_id takes precedence for rate limiting
        mock_rate_limiter.is_rate_limited.assert_called_once()
        rate_limit_identifier = mock_rate_limiter.is_rate_limited.call_args.args[0]
        assert rate_limit_identifier == user_id  # Not session_id

    def test_report_content_missing_required_fields(
        self, client: TestClient, mock_rate_limiter
    ):
        """Test validation for required fields."""
        session_id = str(uuid.uuid4())

        # Missing content_id
        response = client.post(
            "/api/v1/moderation/report",
            json={"content_type": "commentary", "reason": "spam"},
            headers={"X-User": "anonymous", "X-Session-Id": session_id},
        )
        assert response.status_code == 422

        # Missing content_type
        response = client.post(
            "/api/v1/moderation/report",
            json={"content_id": str(uuid.uuid4()), "reason": "spam"},
            headers={"X-User": "anonymous", "X-Session-Id": session_id},
        )
        assert response.status_code == 422

        # Missing reason
        response = client.post(
            "/api/v1/moderation/report",
            json={"content_id": str(uuid.uuid4()), "content_type": "commentary"},
            headers={"X-User": "anonymous", "X-Session-Id": session_id},
        )
        assert response.status_code == 422


class TestModerationAdminEndpoints:
    """Test suite for admin-only moderation endpoints."""

    @pytest.fixture
    def mock_moderation_service(self):
        """Mock moderation service for testing."""
        with patch("api.v1.moderation.get_moderation_service") as mock:
            service = Mock()
            mock.return_value = service
            yield service

    def test_get_pending_reports_requires_admin(self, client: TestClient):
        """Test only admins can access pending reports."""
        # Non-admin user
        response = client.get(
            "/api/v1/moderation/reports",
            headers={"X-User": "regular-user", "X-Is-Admin": "false"},
        )
        assert response.status_code == 403

    def test_delete_content_requires_admin(self, client: TestClient):
        """Test only admins can delete content."""
        response = client.delete(
            f"/api/v1/moderation/content/commentary/{uuid.uuid4()}",
            headers={"X-User": "regular-user", "X-Is-Admin": "false"},
        )
        assert response.status_code == 403

    def test_dismiss_report_requires_admin(self, client: TestClient):
        """Test only admins can dismiss reports."""
        response = client.put(
            f"/api/v1/moderation/reports/{uuid.uuid4()}/dismiss",
            headers={"X-User": "regular-user", "X-Is-Admin": "false"},
        )
        assert response.status_code == 403
