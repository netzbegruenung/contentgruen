"""
Unit tests for URL validation and sanitization utilities
"""

import pytest
from utils.url_validator import (
    validate_url_security,
    sanitize_url,
    BLACKLISTED_PROTOCOLS,
)


class TestUrlValidator:
    """Test suite for URL validation utilities"""

    def test_validate_url_security_valid_urls(self):
        """Test validation of valid URLs"""
        valid_urls = [
            ("https://www.example.com", (True, "")),
            ("http://example.org/path", (True, "")),
            ("https://subdomain.example.com:8080/path?query=1", (True, "")),
            ("ftp://ftp.example.com", (True, "")),
        ]

        for url, expected in valid_urls:
            result = validate_url_security(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_validate_url_security_blacklisted_protocols(self):
        """Test rejection of blacklisted protocols"""
        for protocol in BLACKLISTED_PROTOCOLS:
            url = f"{protocol}://example.com"
            is_valid, error = validate_url_security(url)
            assert is_valid is False
            assert f"Protocol '{protocol}' is not allowed" in error

    def test_validate_url_security_localhost_variations(self):
        """Test rejection of localhost URLs"""
        localhost_urls = [
            "http://localhost/",
            "https://127.0.0.1:8080/",
            "http://[::1]/",
            "https://LOCALHOST/",
        ]

        for url in localhost_urls:
            is_valid, error = validate_url_security(url)
            assert is_valid is False
            assert "localhost are not allowed" in error

    def test_validate_url_security_private_ips(self):
        """Test rejection of private IP addresses"""
        private_ip_urls = [
            "http://10.0.0.1/",
            "https://192.168.1.1/",
            "http://172.16.0.1/",
            "https://169.254.0.1/",
            "http://[fc00::1]/",
            "https://[fd00::1]/",
        ]

        for url in private_ip_urls:
            is_valid, error = validate_url_security(url)
            assert is_valid is False
            assert "private IP addresses are not allowed" in error

    def test_validate_url_security_path_traversal(self):
        """Test rejection of path traversal patterns"""
        traversal_urls = [
            "http://example.com/../etc/passwd",
            "https://example.com/..\\windows\\system32",
            "http://example.com/path/../../../etc/passwd",
        ]

        for url in traversal_urls:
            is_valid, error = validate_url_security(url)
            assert is_valid is False
            assert "Path traversal patterns are not allowed" in error

    def test_validate_url_security_overly_long_url(self):
        """Test rejection of overly long URLs"""
        long_url = "http://example.com/" + "a" * 2048
        is_valid, error = validate_url_security(long_url)
        assert is_valid is False
        assert "URL is too long" in error

    def test_validate_url_security_empty_url(self):
        """Test rejection of empty URL"""
        is_valid, error = validate_url_security("")
        assert is_valid is False
        assert "URL cannot be empty" in error

        is_valid, error = validate_url_security(None)
        assert is_valid is False
        assert "URL cannot be empty" in error

    def test_sanitize_url_removes_dangerous_fragments(self):
        """Test sanitization of dangerous fragments"""
        dangerous_urls = [
            ("http://example.com#<script>alert(1)</script>", "http://example.com"),
            ("https://example.com#onclick='alert(1)'", "https://example.com"),
            ('http://example.com#"dangerous"', "http://example.com"),
        ]

        for dangerous_url, expected_clean in dangerous_urls:
            sanitized = sanitize_url(dangerous_url)
            assert sanitized == expected_clean

    def test_sanitize_url_cleans_query_parameters(self):
        """Test sanitization of query parameters"""
        dangerous_urls = [
            ("http://example.com?q=<script>", "http://example.com?q=script"),
            ("https://example.com?name='test'", "https://example.com?name=test"),
            ('http://example.com?val="test"', "http://example.com?val=test"),
        ]

        for dangerous_url, expected_clean in dangerous_urls:
            sanitized = sanitize_url(dangerous_url)
            assert sanitized == expected_clean

    def test_sanitize_url_removes_null_bytes(self):
        """Test removal of null bytes"""
        url_with_null = "http://example.com/path\x00/file"
        sanitized = sanitize_url(url_with_null)
        assert "\x00" not in sanitized
        assert sanitized == "http://example.com/path/file"

    def test_sanitize_url_handles_empty_input(self):
        """Test sanitization of empty input"""
        assert sanitize_url("") == ""
        assert sanitize_url(None) == None

    def test_sanitize_url_preserves_valid_urls(self):
        """Test that valid URLs are preserved"""
        valid_urls = [
            "https://www.example.com/path?query=value&param=123",
            "http://subdomain.example.org:8080/api/v1/resource",
            "https://example.com/path/to/resource#section",
        ]

        for url in valid_urls:
            sanitized = sanitize_url(url)
            assert sanitized == url
