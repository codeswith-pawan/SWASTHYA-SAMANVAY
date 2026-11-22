import json
from pathlib import Path
from datetime import datetime

import hashlib
import json
import os
import secrets
from pathlib import Path
from datetime import datetime


def get_store_path() -> Path:
    env_path = os.getenv("SIH_USERS_PATH")
    if env_path:
        return Path(env_path)
    return Path("data/runtime/users.json")


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations
    and a random 16-byte salt.
    """
    salt = secrets.token_hex(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2:sha256:{iterations}${salt}${derived}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify plain password against stored hash. Supports backward
    compatibility with legacy plain text passwords.
    """
    if not stored_hash:
        return False

    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False
            algorithm_info, salt, expected_derived = parts
            iterations = int(algorithm_info.split(":")[-1])
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            ).hex()
            return secrets.compare_digest(derived, expected_derived)
        except Exception:
            return False

    # Prototype legacy fallback
    return secrets.compare_digest(plain_password, stored_hash)


def _load_users():
    store_path = get_store_path()
    if not store_path.exists():
        return []

    try:
        with open(store_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def _save_users(users):
    store_path = get_store_path()
    store_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(store_path, "w", encoding="utf-8") as file:
        json.dump(
            users,
            file,
            indent=2,
            ensure_ascii=False
        )


def seed_default_users():
    users = _load_users()

    existing_usernames = {u["username"] for u in users}

    default_users = [
        {
            "user_id": "USR000001",
            "username": "gh00046",
            "password": hash_password("hospital123"),
            "name": "Regional Amritsar Medical College Hospital",
            "role": "HOSPITAL",
            "hospital_id": "GH00046",
            "state": "Punjab",
            "district": "Amritsar",
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000002",
            "username": "gh00119",
            "password": hash_password("hospital123"),
            "name": "District Amritsar Medical College Hospital",
            "role": "HOSPITAL",
            "hospital_id": "GH00119",
            "state": "Punjab",
            "district": "Amritsar",
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000003",
            "username": "punjab_admin",
            "password": hash_password("admin123"),
            "name": "Punjab State Health Administration",
            "role": "STATE_ADMIN",
            "hospital_id": None,
            "state": "Punjab",
            "district": None,
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000004",
            "username": "central_admin",
            "password": hash_password("central123"),
            "name": "National Hospital Referral Administration",
            "role": "CENTRAL_ADMIN",
            "hospital_id": None,
            "state": None,
            "district": None,
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000005",
            "username": "gh_test_other",
            "password": hash_password("hospital123"),
            "name": "Test Other Hospital",
            "role": "HOSPITAL",
            "hospital_id": "GH_TEST_OTHER",
            "state": "Punjab",
            "district": "Ludhiana",
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000006",
            "username": "amritsar_district_admin",
            "password": hash_password("district123"),
            "name": "Amritsar District Health Administration",
            "role": "DISTRICT_ADMIN",
            "hospital_id": None,
            "state": "Punjab",
            "district": "Amritsar",
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000007",
            "username": "ludhiana_district_admin",
            "password": hash_password("district123"),
            "name": "Ludhiana District Health Administration",
            "role": "DISTRICT_ADMIN",
            "hospital_id": None,
            "state": "Punjab",
            "district": "Ludhiana",
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR000008",
            "username": "maharashtra_admin",
            "password": hash_password("admin123"),
            "name": "Maharashtra State Health Administration",
            "role": "STATE_ADMIN",
            "hospital_id": None,
            "state": "Maharashtra",
            "district": None,
            "created_at": datetime.now().isoformat(),
        },
        {
            "user_id": "USR_GH99927",
            "username": "gh99927",
            "password": hash_password("Hospital@123"),
            "name": "Purnea Hospital Admin",
            "role": "HOSPITAL",
            "hospital_id": "GH99927",
            "state": "Bihar",
            "district": "Purnia",
            "created_at": datetime.now().isoformat(),
        },
    ]

    # If users file is empty, initialize all
    if not users:
        _save_users(default_users)
        return default_users

    # If some default users (e.g. district admins) are missing from existing store, append them
    updated = False
    for default_user in default_users:
        if default_user["username"] not in existing_usernames:
            users.append(default_user)
            updated = True

    if updated:
        _save_users(users)

    return users


# Static pre-computed dummy hash with 100,000 PBKDF2 iterations for timing attack mitigation
DUMMY_PBKDF2_HASH = (
    "pbkdf2:sha256:100000$0123456789abcdef0123456789abcdef$"
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)


def authenticate_user(username, password):
    users = seed_default_users()

    matched_user = None
    for user in users:
        if user["username"] == username:
            matched_user = user
            break

    if matched_user is not None:
        if verify_password(password, matched_user["password"]):
            # Upgrade legacy plain text password to hashed format if needed
            if not matched_user["password"].startswith("pbkdf2:sha256:"):
                matched_user["password"] = hash_password(password)
                _save_users(users)
            return matched_user
        return None

    # Check relational database users if available (activated provisioned users)
    try:
        from src.database.db_manager import get_session_factory
        SessionFactory = get_session_factory()
        with SessionFactory() as db_session:
            from sqlalchemy import func
            from src.database.pg_models import User
            db_user = db_session.query(User).filter(
                (User.username == username) | (func.lower(User.username) == username.strip().lower())
            ).first()
            if db_user and db_user.is_active and verify_password(password, db_user.password_hash):
                return {
                    "user_id": db_user.user_id,
                    "username": db_user.username,
                    "name": db_user.name,
                    "role": db_user.role_id,
                    "hospital_id": db_user.hospital_id,
                    "state": db_user.state,
                    "district": db_user.district,
                    "password": db_user.password_hash,
                }
    except Exception:
        pass

    # Timing attack defense: verify against dummy hash to prevent username enumeration
    verify_password(password, DUMMY_PBKDF2_HASH)
    return None


def get_user_by_id(user_id):
    users = seed_default_users()

    for user in users:
        if user["user_id"] == user_id:
            return user

    # Check relational database users if available
    try:
        from src.database.db_manager import get_session_factory
        SessionFactory = get_session_factory()
        with SessionFactory() as db_session:
            from src.database.pg_models import User
            db_user = db_session.query(User).filter_by(user_id=user_id).first()
            if db_user:
                return {
                    "user_id": db_user.user_id,
                    "username": db_user.username,
                    "name": db_user.name,
                    "role": db_user.role_id,
                    "hospital_id": db_user.hospital_id,
                    "state": db_user.state,
                    "district": db_user.district,
                    "password": db_user.password_hash,
                }
    except Exception:
        pass

    return None