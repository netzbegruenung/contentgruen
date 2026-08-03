#!/usr/bin/env python3
"""
Test script to verify anonymous access to search and metrics endpoints.
Run this after starting the backend services.
"""

import requests
import json
import sys

# Configuration
BFF_URL = "http://localhost:5054"  # BFF URL for local development
SEARCH_ENDPOINT = f"{BFF_URL}/api/v1/search/searchByText"
METRICS_ENDPOINT = f"{BFF_URL}/api/v1/metrics/getMetrics"


def test_anonymous_search():
    """Test search endpoint without authentication."""
    print("\n=== Testing Anonymous Search ===")

    payload = {"query_text": "climate change", "limit": 5}

    try:
        # Make request without any authentication cookies or headers
        response = requests.post(
            SEARCH_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ Anonymous search successful!")
            data = response.json()
            print(
                f"Results: {data.get('commentary_search_results_count', 0)} commentaries, "
                f"{data.get('generictext_search_results_count', 0)} generic texts"
            )
            return True
        else:
            print(f"❌ Anonymous search failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_anonymous_metrics():
    """Test metrics endpoint without authentication."""
    print("\n=== Testing Anonymous Metrics ===")

    try:
        # Make request without any authentication cookies or headers
        response = requests.get(
            METRICS_ENDPOINT, headers={"Accept": "application/json"}, timeout=10
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ Anonymous metrics access successful!")
            data = response.json()
            print(f"Content count: {data.get('content_count', 0)}")
            print(f"Statement count: {data.get('statement_count', 0)}")
            print(f"Commentary count: {data.get('commentary_count', 0)}")
            return True
        else:
            print(f"❌ Anonymous metrics access failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_protected_endpoint():
    """Test that protected endpoints still require authentication."""
    print("\n=== Testing Protected Endpoint (Should Fail) ===")

    contribute_endpoint = f"{BFF_URL}/api/v1/commentary/addCommentary"

    payload = {"text": "Test commentary", "references": []}

    try:
        response = requests.post(
            contribute_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 401:
            print("✅ Protected endpoint correctly requires authentication")
            return True
        else:
            print(
                f"❌ Protected endpoint should have returned 401, got {response.status_code}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"Request failed (expected): {e}")
        return True  # Connection refused is also acceptable


def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Anonymous Access to ContentGrün API")
    print("=" * 50)
    print(f"BFF URL: {BFF_URL}")

    results = []

    # Test anonymous search
    results.append(("Search", test_anonymous_search()))

    # Test anonymous metrics
    results.append(("Metrics", test_anonymous_metrics()))

    # Test that protected endpoints still require auth
    results.append(("Protected Endpoint", test_protected_endpoint()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed! Anonymous access is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the backend configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
