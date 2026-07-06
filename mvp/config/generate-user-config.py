#!/usr/bin/env python3
"""
Generate managed-users.json from user-passwords.txt
This script reads plaintext passwords and generates a JSON file with BCrypt hashes.

Usage: python generate-user-config.py
"""

import json
import bcrypt
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

def generate_user_config():
    """Generate managed-users.json from user-passwords.txt"""

    # Check if bcrypt is installed
    try:
        import bcrypt
    except ImportError:
        print("ERROR: bcrypt not installed!")
        print("Please install it with: pip install bcrypt")
        sys.exit(1)

    passwords_file = Path("user-passwords.txt")
    output_file = Path("managed-users.json")

    if not passwords_file.exists():
        print(f"ERROR: {passwords_file} not found!")
        print("Please create a file with format: email:password:displayName")
        sys.exit(1)

    users = []
    user_counter = 1

    print("Generating user configuration...")
    print("-" * 50)

    with open(passwords_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse line
            parts = line.split(':')
            if len(parts) != 3:
                print(f"WARNING: Line {line_num} invalid format (expected email:password:displayName)")
                print(f"  Got: {line}")
                continue

            email, password, display_name = parts

            # Generate BCrypt hash (cost factor 12)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

            # Create user object
            user = {
                "email": email.strip(),
                "passwordHash": password_hash.decode('utf-8'),
                "displayName": display_name.strip(),
                "userId": f"user-{user_counter:03d}",
                "createdAt": (datetime.now(timezone.utc) - timedelta(days=user_counter)).isoformat()
            }

            users.append(user)
            print(f"[OK] Generated hash for: {email} ({display_name})")
            user_counter += 1

    # Create final configuration
    config = {
        "users": users,
        "metadata": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "totalUsers": len(users)
        }
    }

    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("-" * 50)
    print(f"[SUCCESS] Generated {output_file}")
    print(f"  Total users: {len(users)}")
    print()
    print("Next steps:")
    print("1. Copy managed-users.json to your server")
    print("2. Place it in: mvp/config/managed-users.json")
    print("3. Restart the BFF service to load new users")
    print()
    print("IMPORTANT: Never commit user-passwords.txt to git!")

    # Add to .gitignore if not already there
    gitignore_path = Path("../../.gitignore")
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()

        if "user-passwords.txt" not in gitignore_content:
            with open(gitignore_path, 'a') as f:
                f.write("\n# Never commit plaintext passwords\n")
                f.write("**/user-passwords.txt\n")
            print("[OK] Added user-passwords.txt to .gitignore")

if __name__ == "__main__":
    try:
        generate_user_config()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
