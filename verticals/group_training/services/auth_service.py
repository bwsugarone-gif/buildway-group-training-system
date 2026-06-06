"""Password login for the group training MVP."""

from __future__ import annotations

import hashlib
import hmac
import os

from verticals.group_training.models import User
from verticals.group_training.services.repository import GroupTrainingRepository


HASH_NAME = "sha256"
ITERATIONS = 120_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("password is required")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = password_hash.split("$", 3)
        if algorithm != f"pbkdf2_{HASH_NAME}":
            return False
        candidate = hashlib.pbkdf2_hmac(
            HASH_NAME,
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, expected_hex)
    except (TypeError, ValueError):
        return False


class AuthService:
    def __init__(self, repo: GroupTrainingRepository) -> None:
        self.repo = repo

    def authenticate(self, tenant_id: str, email: str, password: str) -> User | None:
        user = self.repo.find_user_by_email(tenant_id, email)
        if not user or not user.password_hash:
            return None
        return user if verify_password(password, user.password_hash) else None

