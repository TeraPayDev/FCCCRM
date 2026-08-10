from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")
    return _password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return _password_hash.verify(password, encoded_hash)
