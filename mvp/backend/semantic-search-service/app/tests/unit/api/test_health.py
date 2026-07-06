"""
Unit tests for health check and statistics endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from api.v1.health import (
    check_database_connection,
    check_qdrant_connection,
    check_disk_space,
    check_memory_usage,
    get_last_backup_time,
)


class TestHealthCheckFunctions:
    """Test suite for health check helper functions."""

    @pytest.mark.asyncio
    async def test_check_database_connection_success(self):
        """Test successful database connection check."""
        with patch("api.v1.health.get_app_database") as mock_get_db:
            mock_db = Mock()
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_db.get_session.return_value.__exit__ = Mock(return_value=False)
            mock_session.execute.return_value = None
            mock_get_db.return_value = mock_db

            result = await check_database_connection()

            assert result["status"] == "healthy"
            assert "Database connection successful" in result["message"]

    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self):
        """Test database connection failure."""
        with patch("api.v1.health.get_app_database") as mock_get_db:
            mock_db = Mock()
            mock_db.get_session.side_effect = Exception("Connection refused")
            mock_get_db.return_value = mock_db

            result = await check_database_connection()

            assert result["status"] == "unhealthy"
            assert result["message"] == "Database connection failed"

    @pytest.mark.asyncio
    async def test_check_qdrant_connection_success(self):
        """Test successful Qdrant connection check."""
        with patch("api.v1.health.get_embeddings_manager") as mock_get_manager:
            mock_manager = AsyncMock()
            mock_health_info = {
                "status": "healthy",
                "vectors_count": 150,
                "total_points": 150,
            }
            mock_manager.health_check.return_value = mock_health_info
            mock_get_manager.return_value = mock_manager

            result = await check_qdrant_connection()

            assert result["status"] == "healthy"
            assert result["vectors_count"] == 150
            # URL and collection no longer exposed for security

    @pytest.mark.asyncio
    async def test_check_qdrant_connection_failure(self):
        """Test Qdrant connection failure."""
        with patch("api.v1.health.get_embeddings_manager") as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.health_check.side_effect = Exception("Cannot connect")
            mock_get_manager.return_value = mock_manager

            result = await check_qdrant_connection()

            assert result["status"] == "unhealthy"
            assert result["message"] == "Qdrant connection failed"

    def test_check_disk_space_healthy(self):
        """Test disk space check when healthy."""
        with patch("api.v1.health.shutil.disk_usage") as mock_disk_usage:
            mock_usage = Mock()
            mock_usage.total = 100 * (1024**3)  # 100 GB
            mock_usage.used = 50 * (1024**3)  # 50 GB
            mock_usage.free = 50 * (1024**3)  # 50 GB
            mock_disk_usage.return_value = mock_usage

            with patch("api.v1.health.settings") as mock_settings:
                mock_settings.metadata_path = "/test/path"

                result = check_disk_space()

                assert result["status"] == "healthy"
                assert result["total_gb"] == 100.0
                assert result["used_gb"] == 50.0
                assert result["free_gb"] == 50.0
                assert result["percent_used"] == 50.0

    def test_check_disk_space_warning(self):
        """Test disk space check when in warning state (>80%)."""
        with patch("api.v1.health.shutil.disk_usage") as mock_disk_usage:
            mock_usage = Mock()
            mock_usage.total = 100 * (1024**3)  # 100 GB
            mock_usage.used = 85 * (1024**3)  # 85 GB
            mock_usage.free = 15 * (1024**3)  # 15 GB
            mock_disk_usage.return_value = mock_usage

            with patch("api.v1.health.settings") as mock_settings:
                mock_settings.metadata_path = "/test/path"

                result = check_disk_space()

                assert result["status"] == "warning"
                assert result["percent_used"] == 85.0

    def test_check_disk_space_critical(self):
        """Test disk space check when critical (>90%)."""
        with patch("api.v1.health.shutil.disk_usage") as mock_disk_usage:
            mock_usage = Mock()
            mock_usage.total = 100 * (1024**3)  # 100 GB
            mock_usage.used = 95 * (1024**3)  # 95 GB
            mock_usage.free = 5 * (1024**3)  # 5 GB
            mock_disk_usage.return_value = mock_usage

            with patch("api.v1.health.settings") as mock_settings:
                mock_settings.metadata_path = "/test/path"

                result = check_disk_space()

                assert result["status"] == "critical"
                assert result["percent_used"] == 95.0

    def test_check_memory_usage_healthy(self):
        """Test memory usage check when healthy."""
        with patch("api.v1.health.psutil.virtual_memory") as mock_memory:
            mock_mem = Mock()
            mock_mem.total = 16 * (1024**3)  # 16 GB
            mock_mem.used = 8 * (1024**3)  # 8 GB
            mock_mem.available = 8 * (1024**3)  # 8 GB
            mock_mem.percent = 50.0
            mock_memory.return_value = mock_mem

            result = check_memory_usage()

            assert result["status"] == "healthy"
            assert result["total_gb"] == 16.0
            assert result["used_gb"] == 8.0
            assert result["available_gb"] == 8.0
            assert result["percent_used"] == 50.0

    def test_check_memory_usage_warning(self):
        """Test memory usage check when in warning state (>80%)."""
        with patch("api.v1.health.psutil.virtual_memory") as mock_memory:
            mock_mem = Mock()
            mock_mem.total = 16 * (1024**3)  # 16 GB
            mock_mem.used = 13.6 * (1024**3)  # 13.6 GB
            mock_mem.available = 2.4 * (1024**3)  # 2.4 GB
            mock_mem.percent = 85.0
            mock_memory.return_value = mock_mem

            result = check_memory_usage()

            assert result["status"] == "warning"
            assert result["percent_used"] == 85.0

    def test_check_memory_usage_critical(self):
        """Test memory usage check when critical (>90%)."""
        with patch("api.v1.health.psutil.virtual_memory") as mock_memory:
            mock_mem = Mock()
            mock_mem.total = 16 * (1024**3)  # 16 GB
            mock_mem.used = 15.2 * (1024**3)  # 15.2 GB
            mock_mem.available = 0.8 * (1024**3)  # 0.8 GB
            mock_mem.percent = 95.0
            mock_memory.return_value = mock_mem

            result = check_memory_usage()

            assert result["status"] == "critical"
            assert result["percent_used"] == 95.0

    def test_get_last_backup_time_daily_exists(self):
        """Test getting last backup time when daily backup exists."""
        with patch("api.v1.health.os.path.exists") as mock_exists:
            with patch("api.v1.health.os.path.islink") as mock_islink:
                with patch("api.v1.health.os.readlink") as mock_readlink:
                    with patch("api.v1.health.os.path.getmtime") as mock_getmtime:
                        # Mock the full path properly
                        def exists_side_effect(path):
                            return (
                                "daily/latest" in path
                                or "daily\\latest" in path
                                or "backup_20251008_120000" in path
                            )

                        mock_exists.side_effect = exists_side_effect
                        mock_islink.return_value = True
                        mock_readlink.return_value = "backup_20251008_120000"
                        mock_getmtime.return_value = 1728388800.0  # Fixed timestamp

                        result = get_last_backup_time()

                        assert result is not None
                        assert isinstance(result, str)
                        # Should be ISO format datetime string
                        datetime.fromisoformat(result)

    def test_get_last_backup_time_no_backup(self):
        """Test getting last backup time when no backup exists."""
        with patch("api.v1.health.os.path.exists") as mock_exists:
            mock_exists.return_value = False

            result = get_last_backup_time()

            assert result is None

    def test_get_last_backup_time_error(self):
        """Test getting last backup time when error occurs."""
        with patch("api.v1.health.os.path.exists") as mock_exists:
            mock_exists.side_effect = Exception("Permission denied")

            result = get_last_backup_time()

            assert result is None
