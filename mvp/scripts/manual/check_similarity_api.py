#!/usr/bin/env python3
"""
Test script for the similarity API endpoint.
Run this after starting the semantic-search-service to verify the implementation.

Usage:
    python mvp/scripts/manual/check_similarity_api.py
"""

import requests
import json

API_URL = "http://localhost:8000/api/v1/test/similarity"


def test_similarity(text1: str, text2: str, mode: str = "default"):
    """Test similarity between two texts."""
    payload = {
        "text1": text1,
        "text2": text2,
        "prefix_mode": mode,
        "include_embeddings": False,
    }

    print(f"\n{'='*80}")
    print(f"Testing: {mode}")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"{'='*80}")

    response = requests.post(API_URL, json=payload)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Similarity Score: {result['similarity_score']:.4f}")
        print(f"   Text1 prefix: {result['text1_prefix']}")
        print(f"   Text2 prefix: {result['text2_prefix']}")
        return result["similarity_score"]
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 80)
    print("Similarity API Test Suite")
    print("=" * 80)

    # Test 1: Similar statements (should be high with query-query)
    text1 = "Klimaschutz ist wichtig"
    text2 = "Der Klimaschutz ist sehr wichtig"

    score_qq = test_similarity(text1, text2, "query-query")
    score_pp = test_similarity(text1, text2, "passage-passage")
    score_qp = test_similarity(text1, text2, "query-passage")

    if score_qq and score_pp and score_qp:
        print(f"\n📊 Comparison for similar statements:")
        print(f"   query-query:      {score_qq:.4f}")
        print(f"   passage-passage:  {score_pp:.4f}")
        print(f"   query-passage:    {score_qp:.4f}")

    # Test 2: Different topics
    text1 = "Klimaschutz ist wichtig"
    text2 = "Digitalisierung in Schulen fördern"

    print(f"\n\n{'='*80}")
    print("Testing different topics:")
    print(f"{'='*80}")
    score = test_similarity(text1, text2, "query-query")
    if score:
        print(f"\n📊 Different topics should have low similarity: {score:.4f}")

    # Test 3: Query vs longer passage (production scenario)
    text1 = "Klimaschutz"
    text2 = "Der Klimaschutz umfasst alle Maßnahmen zur Bekämpfung des Klimawandels, einschließlich der Reduktion von CO2-Emissionen"

    print(f"\n\n{'='*80}")
    print("Testing query vs passage (production scenario):")
    print(f"{'='*80}")
    score = test_similarity(text1, text2, "query-passage")
    if score:
        print(f"\n📊 Query-passage similarity: {score:.4f}")

    print(f"\n{'='*80}")
    print("✅ Test suite completed!")
    print(f"{'='*80}")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API at " + API_URL)
        print("   Make sure the semantic-search-service is running on port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
