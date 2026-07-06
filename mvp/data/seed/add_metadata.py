"""
Script to add realistic metadata to seed data files.
Adds usage_count and created_at fields to make the data look more realistic.
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

def generate_realistic_metadata():
    """Generate realistic metadata for a content item."""
    # Random usage count between 2-17 for more realism
    usage_count = random.randint(2, 17)

    # Created date within last 2 weeks, spread out
    days_ago = random.randint(1, 14)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)

    created_at = datetime.now() - timedelta(
        days=days_ago,
        hours=hours_ago,
        minutes=minutes_ago
    )

    return {
        "usage_count": usage_count,
        "created_at": created_at.isoformat()
    }

def add_metadata_to_file(file_path):
    """Add metadata to a seed data file."""
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add metadata to each statement
    for item in data:
        if "metadata" not in item:
            item["metadata"] = generate_realistic_metadata()

        # Also add metadata to each commentary if they exist
        if "commentaries" in item:
            for commentary in item["commentaries"]:
                if "metadata" not in commentary:
                    # Commentaries might have slightly lower usage
                    commentary["metadata"] = {
                        "usage_count": random.randint(1, 10),
                        "created_at": (datetime.now() - timedelta(
                            days=random.randint(1, 14),
                            hours=random.randint(0, 23)
                        )).isoformat()
                    }

    # Write back with nice formatting
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"  Added metadata to {len(data)} items")

def add_metadata_to_generictext_file(file_path):
    """Add metadata to a generic text seed data file."""
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add metadata to each statement
    for item in data:
        if "metadata" not in item:
            item["metadata"] = generate_realistic_metadata()

        # Also add metadata to each generic_text if they exist
        if "generic_texts" in item:
            for generic_text in item["generic_texts"]:
                if "metadata" not in generic_text:
                    # Generic texts might have slightly lower usage
                    generic_text["metadata"] = {
                        "usage_count": random.randint(1, 8),
                        "created_at": (datetime.now() - timedelta(
                            days=random.randint(1, 14),
                            hours=random.randint(0, 23)
                        )).isoformat()
                    }

    # Write back with nice formatting
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"  Added metadata to {len(data)} items")

def main():
    """Main function to process all v1.0 seed data files."""

    # Process statements with commentaries
    seed_path = Path(__file__).parent / "v1.0" / "statements_with_commentaries"

    if not seed_path.exists():
        print(f"Error: Path {seed_path} does not exist")
        return

    # Process all JSON files
    json_files = list(seed_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {seed_path}")
        return

    print(f"Found {len(json_files)} JSON files to process")
    print("-" * 50)

    for json_file in json_files:
        add_metadata_to_file(json_file)

    print("-" * 50)
    print(f"Successfully processed {len(json_files)} commentary files")

    # Process statements with generic texts
    generictext_path = Path(__file__).parent / "v1.0" / "statements_with_generictexts"

    if generictext_path.exists():
        print("\n" + "-" * 50)
        print("Processing generic text files...")
        print("-" * 50)

        generictext_files = list(generictext_path.glob("*.json"))

        for json_file in generictext_files:
            add_metadata_to_generictext_file(json_file)

        print("-" * 50)
        print(f"Successfully processed {len(generictext_files)} generic text files")

    print("\nAll seed data files have been updated with metadata!")

if __name__ == "__main__":
    main()
