import argparse
import getpass
import sys

from src.auth import (
    CredentialStoreError,
    hash_password,
    load_teacher_hashes,
    save_teacher_hashes,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage local teacher accounts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set", help="Add or reset a teacher password")
    set_parser.add_argument("username")
    remove_parser = subparsers.add_parser("remove", help="Remove a teacher account")
    remove_parser.add_argument("username")
    args = parser.parse_args()

    try:
        teachers = load_teacher_hashes()
    except FileNotFoundError:
        teachers = {}
    except CredentialStoreError as exc:
        print(f"Cannot read teacher accounts: {exc}", file=sys.stderr)
        return 1

    username = args.username.strip()
    if not username:
        print("Username cannot be empty.", file=sys.stderr)
        return 1

    if args.command == "set":
        password = getpass.getpass("Teacher password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if not password:
            print("Password cannot be empty.", file=sys.stderr)
            return 1
        if password != confirmation:
            print("Passwords do not match.", file=sys.stderr)
            return 1
        teachers[username] = hash_password(password)
    else:
        if username not in teachers:
            print(f"Teacher account '{username}' was not found.", file=sys.stderr)
            return 1
        del teachers[username]

    try:
        save_teacher_hashes(teachers)
    except OSError as exc:
        print(f"Cannot save teacher accounts: {exc}", file=sys.stderr)
        return 1

    print(f"Teacher account '{username}' updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
