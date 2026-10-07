import bcrypt

# bcrypt only looks at the first 72 bytes; bcrypt>=5 raises instead of silently truncating,
# so request schemas must cap password length (enforced in the auth schemas).
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())
