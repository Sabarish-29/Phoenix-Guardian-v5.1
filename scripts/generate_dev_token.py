#!/usr/bin/env python3
"""Generate a development JWT token for testing SAP API endpoints.

Only works when SAP_DEMO_MODE=true or PHOENIX_DEV_MODE=true.

Usage:
    python scripts/generate_dev_token.py
    python scripts/generate_dev_token.py --role admin
    python scripts/generate_dev_token.py --role physician
    python scripts/generate_dev_token.py --role nurse
"""
import argparse
import sys

sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()  # Ensure JWT_SECRET_KEY matches the running server

from phoenix_guardian.api.auth.utils import DEV_USERS, create_access_token


ROLE_MAP = {
    "admin": "admin@phoenixguardian.health",
    "physician": "dr.smith@phoenixguardian.health",
    "nurse": "nurse.jones@phoenixguardian.health",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a dev JWT token")
    parser.add_argument(
        "--role",
        default="admin",
        choices=["admin", "physician", "nurse"],
        help="Role for the dev user (default: admin)",
    )
    args = parser.parse_args()

    email = ROLE_MAP[args.role]
    user_info = DEV_USERS[email]

    token = create_access_token(data={
        "sub": str(user_info["id"]),
        "email": email,
        "role": user_info["role"],
    })

    print(token)


if __name__ == "__main__":
    main()
