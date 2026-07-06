"""
URL validation and sanitization utilities for security.
"""

import re
import logging
from typing import Tuple
from urllib.parse import urlparse, urlunparse, quote

logger = logging.getLogger(__name__)

# Blacklisted protocols that should not be allowed
BLACKLISTED_PROTOCOLS = ["javascript", "data", "vbscript", "file", "about", "blob"]

# Common private/internal IP patterns
PRIVATE_IP_PATTERNS = [
    r"^127\.",  # Loopback
    r"^10\.",  # Private class A
    r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # Private class B
    r"^192\.168\.",  # Private class C
    r"^169\.254\.",  # Link-local
    r"^::1$",  # IPv6 loopback
    r"^fc00:",  # IPv6 private
    r"^fd00:",  # IPv6 private
]


def validate_url_security(url: str) -> Tuple[bool, str]:
    """
    Validate URL for security concerns.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    try:
        parsed = urlparse(url)

        # Check for blacklisted protocols
        if parsed.scheme and parsed.scheme.lower() in BLACKLISTED_PROTOCOLS:
            return False, f"Protocol '{parsed.scheme}' is not allowed"

        # Check for private/internal IPs
        if parsed.hostname:
            hostname = parsed.hostname.lower()

            # Check for localhost variations
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                return False, "Links to localhost are not allowed"

            # Check for private IP patterns
            for pattern in PRIVATE_IP_PATTERNS:
                if re.match(pattern, hostname):
                    return False, "Links to private IP addresses are not allowed"

        # Check for suspicious patterns
        if "../" in url or "..\\" in url:
            return False, "Path traversal patterns are not allowed"

        # Check for overly long URLs (potential buffer overflow attempts)
        if len(url) > 2048:
            return False, "URL is too long (max 2048 characters)"

        return True, ""

    except Exception as e:
        logger.warning(f"Error validating URL '{url}': {e}")
        return False, f"Invalid URL format: {str(e)}"


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing potentially dangerous elements.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)

        # Remove any fragment that might contain scripts
        if parsed.fragment and any(
            char in parsed.fragment for char in ["<", ">", '"', "'"]
        ):
            parsed = parsed._replace(fragment="")

        # Remove any dangerous query parameters
        if parsed.query:
            # Basic sanitization - in production, you'd want more sophisticated filtering
            clean_query = re.sub(r'[<>"\']', "", parsed.query)
            if clean_query != parsed.query:
                logger.warning(f"Sanitized query parameters in URL: {url}")
                parsed = parsed._replace(query=clean_query)

        # Reconstruct URL
        sanitized = urlunparse(parsed)

        # Additional cleanup - remove any null bytes
        sanitized = sanitized.replace("\x00", "")

        return sanitized

    except Exception as e:
        logger.error(f"Error sanitizing URL '{url}': {e}")
        # Raise exception instead of silently returning original URL
        raise ValueError(f"Failed to sanitize URL: {str(e)}")
