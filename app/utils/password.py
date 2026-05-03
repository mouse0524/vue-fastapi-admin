from passlib import pwd
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def is_password_strong(password: str, min_length: int = 8, min_categories: int = 2) -> tuple[bool, str]:
    value = str(password or "")
    if len(value) < min_length:
        return False, f"密码长度至少 {min_length} 位"

    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    has_special = any(not ch.isalnum() for ch in value)
    categories = int(has_letter) + int(has_digit) + int(has_special)
    if categories < min_categories:
        return False, "密码必须包含字母、数字、特殊字符中的任意两类"
    return True, ""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_password() -> str:
    return pwd.genword()


def generate_strong_password(min_length: int = 12, min_categories: int = 2) -> str:
    while True:
        candidate = pwd.genword(length=max(min_length, 8), charset="ascii_72")
        ok, _ = is_password_strong(candidate, min_length=min_length, min_categories=min_categories)
        if ok:
            return candidate
