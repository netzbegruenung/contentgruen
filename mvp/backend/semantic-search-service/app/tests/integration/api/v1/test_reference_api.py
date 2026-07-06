"""
Integration tests for Reference API endpoints.
Focused on critical functionality after simplification.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock

from main import app
from domain.models.reference import ReferenceDbEntry, ReferenceSearchResult
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin


@pytest.mark.integration
class TestReferenceAPI:
    """Test Reference API endpoints with critical coverage."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_reference_service(self):
        """Mock reference service for testing."""
        with patch("api.v1.reference.get_reference_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    def test_add_reference_new(self, client, mock_reference_service):
        """Test adding a new reference."""
        # Setup
        reference_id = uuid.uuid4()
        mock_reference_service.find_exact_match.return_value = None
        mock_reference_service.add_reference.return_value = (
            reference_id,
            True,
            "Created",
        )
        mock_reference_service._extract_domain.return_value = None

        # Execute
        response = client.post(
            "/api/v1/reference/add",
            json={
                "reference_string": "https://example.com/article",
                "description": "Test article",
            },
            headers={"X-User": "testuser"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["was_new"] is True
        assert "id" in data

    def test_add_reference_existing(self, client, mock_reference_service):
        """Test adding a reference that already exists."""
        # Setup
        existing_id = uuid.uuid4()
        existing_ref = MagicMock()
        existing_ref.id = existing_id
        existing_ref.description = "Existing description"
        mock_reference_service.find_exact_match.return_value = existing_ref
        mock_reference_service._extract_domain.return_value = None

        # Execute
        response = client.post(
            "/api/v1/reference/add",
            json={
                "reference_string": "https://example.com/article",
                "description": "New description",
            },
            headers={"X-User": "testuser"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["was_new"] is False
        assert data["existing_description"] == "Existing description"

    def test_add_reference_invalid_url(self, client, mock_reference_service):
        """Test adding a reference with invalid URL."""
        # Setup
        mock_reference_service._extract_domain.return_value = "evil.com"

        # Execute
        response = client.post(
            "/api/v1/reference/add",
            json={
                "reference_string": "javascript:alert('xss')",
                "description": "Malicious",
            },
            headers={"X-User": "testuser"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid reference URL" in response.json()["detail"]

    def test_search_references(self, client, mock_reference_service):
        """Test searching for references."""
        # Setup
        mock_results = [
            MagicMock(
                id=uuid.uuid4(),
                reference_string="https://example.com/1",
                description="First result",
                domain="example.com",
                created="2024-01-01T00:00:00",
                usage_count=5,
                score=0.95,
            ),
            MagicMock(
                id=uuid.uuid4(),
                reference_string="https://example.com/2",
                description="Second result",
                domain="example.com",
                created="2024-01-02T00:00:00",
                usage_count=3,
                score=0.85,
            ),
        ]
        mock_reference_service.search.return_value = mock_results

        # Execute
        response = client.post(
            "/api/v1/reference/search", json={"query_text": "example", "limit": 10}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["reference_string"] == "https://example.com/1"

    def test_search_references_with_exact_match(self, client, mock_reference_service):
        """Test search that finds exact match."""
        # Setup
        exact_id = uuid.uuid4()
        mock_results = [
            MagicMock(
                id=exact_id,
                reference_string="https://exact.match.com",
                description="Exact match",
                domain="exact.match.com",
                created="2024-01-01T00:00:00",
                usage_count=10,
                score=1.0,
            )
        ]
        mock_reference_service.search.return_value = mock_results

        # Execute
        response = client.post(
            "/api/v1/reference/search",
            json={"query_text": "https://exact.match.com", "limit": 10},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_exact_match"] is True
        assert str(data["exact_match_id"]) == str(exact_id)

    def test_get_reference_by_id(self, client, mock_reference_service):
        """Test getting reference by ID."""
        # Setup
        ref_id = uuid.uuid4()
        mock_ref = MagicMock()
        mock_ref.id = ref_id
        mock_ref.reference_string = "https://example.com/ref"
        mock_ref.description = "Test reference"
        mock_ref.text = "Reference text"
        mock_ref.created = "2024-01-01T00:00:00"
        mock_ref.last_modified = "2024-01-01T00:00:00"
        mock_ref.original_author = "testuser"
        mock_ref.usage_count = 5
        mock_ref.domain = "example.com"
        mock_reference_service.get.return_value = mock_ref

        # Execute
        response = client.get(f"/api/v1/reference/getById?reference_id={ref_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["reference_string"] == "https://example.com/ref"
        assert data["usage_count"] == 5

    def test_get_reference_not_found(self, client, mock_reference_service):
        """Test getting non-existent reference."""
        # Setup
        ref_id = uuid.uuid4()
        mock_reference_service.get.return_value = None

        # Execute
        response = client.get(f"/api/v1/reference/getById?reference_id={ref_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_reference_description(self, client, mock_reference_service):
        """Test updating reference description."""
        # Setup
        ref_id = uuid.uuid4()
        mock_ref = MagicMock()
        mock_ref.id = ref_id
        mock_reference_service.get.return_value = mock_ref
        mock_reference_service.update_description.return_value = True

        # Execute
        response = client.post(
            "/api/v1/reference/update-description",
            json={"reference_id": str(ref_id), "description": "Updated description"},
            headers={"X-User": "testuser"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "aktualisiert" in data["message"]

    def test_rate_limiting(self, client, mock_reference_service):
        """Test rate limiting on reference creation."""
        # Setup
        mock_reference_service.find_exact_match.return_value = None
        mock_reference_service.add_reference.return_value = (
            uuid.uuid4(),
            True,
            "Created",
        )
        mock_reference_service._extract_domain.return_value = None

        # Execute - make many requests quickly
        responses = []
        for i in range(35):  # Rate limit is 30 per minute
            response = client.post(
                "/api/v1/reference/add",
                json={
                    "reference_string": f"https://example.com/article{i}",
                    "description": f"Test article {i}",
                },
                headers={"X-User": "ratelimituser"},
            )
            responses.append(response.status_code)

        # Assert - last requests should be rate limited
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses

    def test_missing_user_header(self, client):
        """Test that missing X-User header is handled."""
        response = client.post(
            "/api/v1/reference/add",
            json={
                "reference_string": "https://example.com/article",
                "description": "Test",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "X-User header missing" in response.json()["detail"]
