import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request

PBKDF2_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
_MIN_ACCEPTED_ITERATIONS = 100_000
_MAX_ACCEPTED_ITERATIONS = 1_000_000
_teacher_sessions: dict[str, tuple[str, float]] = {}


class CredentialStoreError(Exception):
    pass


def credential_file_path() -> Path:
    configured_path = os.environ.get("TEACHERS_FILE")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).with_name("teachers.json")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    salt_text = base64.b64encode(salt).decode("ascii")
    hash_text = base64.b64encode(password_hash).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_text}${hash_text}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iteration_text, salt_text, expected_hash_text = encoded_hash.split("$")
        iterations = int(iteration_text)
        if (
            algorithm != "pbkdf2_sha256"
            or not _MIN_ACCEPTED_ITERATIONS <= iterations <= _MAX_ACCEPTED_ITERATIONS
        ):
            return False
        salt = base64.b64decode(salt_text, validate=True)
        expected_hash = base64.b64decode(expected_hash_text, validate=True)
        if len(salt) < 16 or len(expected_hash) != 32:
            return False
    except (AttributeError, ValueError, binascii.Error):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def load_teacher_hashes(path: Path | None = None) -> dict[str, str]:
    file_path = path or credential_file_path()
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialStoreError("Unable to read teacher credentials") from exc

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), dict):
        raise CredentialStoreError("Expected a JSON object with a teachers object")

    teachers = data["teachers"]
    if any(
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password_hash, str)
        for username, password_hash in teachers.items()
    ):
        raise CredentialStoreError("Teacher usernames and password hashes must be strings")
    return teachers


def save_teacher_hashes(teachers: dict[str, str], path: Path | None = None) -> None:
    file_path = path or credential_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps({"teachers": teachers}, indent=2) + "\n"
    temporary_path = file_path.with_name(f".{file_path.name}.{secrets.token_hex(8)}.tmp")

    try:
        temporary_path.write_text(serialized, encoding="utf-8")
        temporary_path.chmod(0o600)
        temporary_path.replace(file_path)
        file_path.chmod(0o600)
    finally:
        temporary_path.unlink(missing_ok=True)


def create_teacher_session(username: str) -> str:
    now = time.time()
    expired_tokens = [
        token for token, (_, expires_at) in _teacher_sessions.items() if expires_at <= now
    ]
    for token in expired_tokens:
        _teacher_sessions.pop(token, None)

    token = secrets.token_urlsafe(32)
    _teacher_sessions[token] = (username, now + SESSION_TTL_SECONDS)
    return token


def get_teacher_session(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    session = _teacher_sessions.get(token)
    if not session:
        return None

    username, expires_at = session
    if expires_at <= time.time():
        _teacher_sessions.pop(token, None)
        return None
    return username


def require_teacher(request: Request) -> str:
    username = get_teacher_session(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


def remove_teacher_session(token: str | None) -> None:
    if token:
        _teacher_sessions.pop(token, None)


def secure_session_cookie() -> bool:
    return os.environ.get("COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"}
