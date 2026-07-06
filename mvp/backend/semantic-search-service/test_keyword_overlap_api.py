#!/usr/bin/env python3
"""
Test script for the keyword overlap API endpoint.
Run this after starting the semantic-search-service to verify keyword overlap boosting.

Usage:
    python test_keyword_overlap_api.py
"""

import requests
import json

API_URL = "http://localhost:8000/api/v1/test/keyword-overlap"


def test_keyword_overlap(
    text1: str, text2: str, similarity_score: float = None, boost_strength: float = 0.3
):
    """Test keyword overlap analysis between two texts."""
    payload = {"text1": text1, "text2": text2, "boost_strength": boost_strength}

    if similarity_score is not None:
        payload["original_similarity_score"] = similarity_score

    print(f"\n{'='*80}")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    if similarity_score is not None:
        print(f"Original Similarity: {similarity_score:.4f}")
    print(f"{'='*80}")

    response = requests.post(API_URL, json=payload)

    if response.status_code == 200:
        result = response.json()

        # Keywords
        print(f"\n📝 Extracted Keywords:")
        print(f"   Text 1: {result['text1_keywords']}")
        print(f"   Text 2: {result['text2_keywords']}")
        print(f"   Matched: {result['matched_keywords']}")

        # Overlap analysis
        print(f"\n🔍 Keyword Overlap:")
        print(f"   Overlap Ratio: {result['overlap_ratio']:.1%}")
        print(
            f"   Keyword Boost: {result['keyword_boost']:.3f} ({(result['keyword_boost']-1)*100:+.1f}%)"
        )

        # Score impact
        if result["original_score"] is not None:
            status = "📈 BOOST" if result["keyword_boost"] > 1.0 else "📉 PENALTY"
            if abs(result["keyword_boost"] - 1.0) < 0.01:
                status = "➡️ NEUTRAL"

            print(f"\n💯 Score Impact: {status}")
            print(f"   Original:   {result['original_score']:.4f}")
            print(f"   Adjusted:   {result['adjusted_score']:.4f}")
            print(f"   Change:     {result['score_change_percent']:+.1f}%")

        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 80)
    print("Keyword Overlap API Test Suite")
    print("=" * 80)

    # Test 1: The problematic case - birds vs reliability
    print("\n\n### TEST 1: Problematic Case - Birds vs Reliability ###")
    print("Expected: LOW overlap → penalty should reduce score significantly")
    test_keyword_overlap(
        "Windräder töten die Vögel!",
        "Erneuerbare Energien sind total unzuverlässig!",
        similarity_score=0.873,
    )

    # Test 2: Perfect match - E-Autos
    print("\n\n### TEST 2: Perfect Match - E-Autos ###")
    print("Expected: HIGH overlap → boost should increase score")
    test_keyword_overlap(
        "E-Autos", "E-Autos sind auch nicht besser für die Umwelt", similarity_score=0.87
    )

    # Test 3: Related but different - Verbrenner-Aus
    print("\n\n### TEST 3: Related but Different - Verbrenner-Aus ###")
    print("Expected: PARTIAL overlap → small penalty")
    test_keyword_overlap(
        "E-Autos",
        "Das Verbrenner-Aus killt unsere Autoindustrie!",
        similarity_score=0.79,
    )

    # Test 4: High overlap - Klimaschutz variations
    print("\n\n### TEST 4: High Overlap - Klimaschutz ###")
    print("Expected: HIGH overlap → boost")
    test_keyword_overlap(
        "Klimaschutz ist wichtig",
        "Der Klimaschutz ist sehr wichtig für unsere Zukunft",
        similarity_score=0.85,
    )

    # Test 5: Low overlap - different topics
    print("\n\n### TEST 5: Low Overlap - Different Topics ###")
    print("Expected: NO overlap → penalty")
    test_keyword_overlap(
        "Klimaschutz fördern",
        "Digitalisierung in Schulen ist wichtig",
        similarity_score=0.75,
    )

    # Test 6: Stemming test - Auto variations
    print("\n\n### TEST 6: Stemming Test - Auto Variations ###")
    print("Expected: HIGH overlap due to stemming (Auto/Autos/Autoindustrie)")
    test_keyword_overlap(
        "Auto kaufen", "Die Autoindustrie produziert viele Autos", similarity_score=0.80
    )

    # Test 7: Renewable energy variations
    print("\n\n### TEST 7: Renewable Energy Variations ###")
    print("Expected: MEDIUM overlap (erneuerbare matches)")
    test_keyword_overlap(
        "Erneuerbare Energien ausbauen",
        "Erneuerbare Energien sind unzuverlässig",
        similarity_score=0.88,
    )

    # Test 8: Wind turbines - direct topic match
    print("\n\n### TEST 8: Wind Turbines - Direct Topic Match ###")
    print("Expected: HIGH overlap (Windräder/Windkraft match)")
    test_keyword_overlap(
        "Windräder sind laut",
        "Windkraft ist eine gute Energiequelle",
        similarity_score=0.82,
    )

    # Test 9: No keywords case
    print("\n\n### TEST 9: Short Query - E-Auto ###")
    print("Expected: HIGH overlap for exact match")
    test_keyword_overlap("E-Auto", "E-Auto Förderung stoppen", similarity_score=0.85)

    # Test 10: Complex statement
    print("\n\n### TEST 10: Complex Statement ###")
    print("Expected: MEDIUM overlap")
    test_keyword_overlap(
        "Die Windräder töten viele Vögel und Insekten",
        "Windkraftanlagen gefährden die Vogelwelt erheblich",
        similarity_score=0.86,
    )

    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETED")
    print("=" * 80)
    print("\nSummary:")
    print("  • Keyword overlap boosting helps distinguish topically different results")
    print("  • High overlap (>50%) → boost score")
    print("  • Low overlap (<50%) → penalize score")
    print("  • German stemming captures word variations (Auto/Autos/Autoindustrie)")
    print("  • Default boost strength: 0.3 (±30% score adjustment)")
    print(
        "\nConfiguration: SEMANTIC_SEARCH_ENABLE_KEYWORD_OVERLAP_BOOST=true/false"
    )
    print("               SEMANTIC_SEARCH_KEYWORD_OVERLAP_BOOST_STRENGTH=0.0-1.0")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API at " + API_URL)
        print("   Make sure the semantic-search-service is running on port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
