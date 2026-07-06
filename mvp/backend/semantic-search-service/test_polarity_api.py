#!/usr/bin/env python3
"""
Test script for the polarity API endpoint.
Run this after starting the semantic-search-service to verify polarity filtering.

Usage:
    python test_polarity_api.py
"""

import requests
import json

API_URL = "http://localhost:8000/api/v1/test/polarity"


def test_polarity(text1: str, text2: str, similarity_score: float = None):
    """Test polarity analysis between two texts."""
    payload = {
        "text1": text1,
        "text2": text2,
    }

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

        # Text 1 analysis
        t1 = result["text1_analysis"]
        print(f"\n📊 Text 1 Analysis:")
        print(f"   Polarity:    {t1['polarity'].upper()}")
        print(f"   Confidence:  {t1['confidence']:.2f}")
        print(f"   Negation:    {'Yes' if t1['negation_detected'] else 'No'}")
        if t1["negative_stance_words"]:
            print(f"   Negative words: {', '.join(t1['negative_stance_words'])}")
        print(f"   Explanation: {t1['explanation']}")

        # Text 2 analysis
        t2 = result["text2_analysis"]
        print(f"\n📊 Text 2 Analysis:")
        print(f"   Polarity:    {t2['polarity'].upper()}")
        print(f"   Confidence:  {t2['confidence']:.2f}")
        print(f"   Negation:    {'Yes' if t2['negation_detected'] else 'No'}")
        if t2["negative_stance_words"]:
            print(f"   Negative words: {', '.join(t2['negative_stance_words'])}")
        print(f"   Explanation: {t2['explanation']}")

        # Comparison
        print(f"\n🔍 Polarity Comparison:")
        match_status = "✅ MATCH" if result["polarities_match"] else "❌ MISMATCH"
        print(f"   Status:      {match_status}")
        print(f"   Penalty:     {result['polarity_penalty']:.2f}")

        if result["original_score"] is not None:
            print(f"\n💯 Score Impact:")
            print(f"   Original:    {result['original_score']:.4f}")
            print(f"   Adjusted:    {result['adjusted_score']:.4f}")
            print(f"   Reduction:   {result['score_reduction_percent']:.1f}%")

        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 80)
    print("Polarity API Test Suite")
    print("=" * 80)

    # Test 1: Matching positive polarities
    print("\n\n### TEST 1: Matching Positive Polarities ###")
    test_polarity(
        "Klimaschutz ist wichtig",
        "Klimaschutz fördern ist notwendig",
        similarity_score=0.85,
    )

    # Test 2: Contradictory polarities (negation)
    print("\n\n### TEST 2: Contradictory Polarities (Negation) ###")
    test_polarity(
        "Klimaschutz ist wichtig",
        "Klimaschutz ist nicht wichtig",
        similarity_score=0.92,
    )

    # Test 3: Contradictory polarities (negative stance words)
    print("\n\n### TEST 3: Contradictory Polarities (Negative Stance) ###")
    test_polarity(
        "Klimaschutz ist wichtig", "Klimaschutz ist überbewertet", similarity_score=0.88
    )

    # Test 4: Neutral query
    print("\n\n### TEST 4: Neutral Query ###")
    test_polarity(
        "Klimaschutz", "Klimaschutz ist sehr wichtig", similarity_score=0.80
    )

    # Test 5: Action verbs - matching
    print("\n\n### TEST 5: Action Verbs - Matching ###")
    test_polarity("Migration fördern", "Migration unterstützen", similarity_score=0.87)

    # Test 6: Action verbs - contradictory
    print("\n\n### TEST 6: Action Verbs - Contradictory ###")
    test_polarity("Migration fördern", "Migration verhindern", similarity_score=0.89)

    # Test 7: Renewable energy - positive
    print("\n\n### TEST 7: Renewable Energy - Positive ###")
    test_polarity(
        "Erneuerbare Energien sind wichtig",
        "Erneuerbare Energien ausbauen",
        similarity_score=0.86,
    )

    # Test 8: Renewable energy - negative
    print("\n\n### TEST 8: Renewable Energy - Negative ###")
    test_polarity(
        "Erneuerbare Energien sind wichtig",
        "Erneuerbare Energien sind nicht wichtig",
        similarity_score=0.91,
    )

    # Test 9: Digitalization - positive
    print("\n\n### TEST 9: Digitalization - Positive ###")
    test_polarity(
        "Digitalisierung ist sinnvoll",
        "Digitalisierung fördern",
        similarity_score=0.84,
    )

    # Test 10: Digitalization - negative
    print("\n\n### TEST 10: Digitalization - Negative ###")
    test_polarity(
        "Digitalisierung ist sinnvoll",
        "Digitalisierung ist unsinnig",
        similarity_score=0.90,
    )

    # Test 11: Negation cancelation
    print("\n\n### TEST 11: Negation Cancelation (nicht nur) ###")
    test_polarity(
        "Klimaschutz ist wichtig",
        "Nicht nur Klimaschutz ist wichtig",
        similarity_score=0.82,
    )

    # Test 12: Without similarity score
    print("\n\n### TEST 12: Analysis Only (No Similarity Score) ###")
    test_polarity("Klimaschutz ist wichtig", "Klimaschutz ablehnen")

    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETED")
    print("=" * 80)
    print("\nNote: The polarity filtering system is designed to:")
    print("  • Detect negations (nicht, kein, nie, etc.)")
    print("  • Identify stance words (wichtig, überbewertet, fördern, verhindern, etc.)")
    print("  • Apply penalties to contradictory results (positive vs negative)")
    print("  • Allow neutral queries/results without penalty")
    print("  • Reduce scores by 20-80% depending on confidence in polarity detection")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API at " + API_URL)
        print("   Make sure the semantic-search-service is running on port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
