"""Assign a teacher password without storing plaintext credentials."""

import argparse
import getpass
import json
import os
import tempfile
from pathlib import Path

from .auth import TEACHERS_FILE, password_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()
    if not args.username.strip() or len(args.username) > 100:
        parser.error("Username must contain 1 to 100 characters and not be blank")
    password = getpass.getpass("New password (at least 12 characters): ")
    if not 12 <= len(password) <= 1024:
        parser.error("Password must contain 12 to 1024 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    path = Path(os.environ.get("TEACHERS_FILE", str(TEACHERS_FILE)))
    teachers = json.loads(path.read_text()) if path.exists() else {}
    teachers[args.username] = password_record(password)
    # Atomic replacement keeps credentials readable during updates.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(teachers, file, indent=2)
            file.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Credentials assigned for {args.username}. Restart the server to revoke old sessions.")


if __name__ == "__main__":
    main()
