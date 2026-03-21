from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


ENCRYPTED_PREFIX = 'enc::'


def _get_cipher():
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def is_encrypted_value(value):
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def encrypt_value(value):
    if not value:
        return value
    if is_encrypted_value(value):
        return value

    cipher = _get_cipher()
    if cipher is None:
        return value

    encrypted = cipher.encrypt(str(value).encode()).decode()
    return f'{ENCRYPTED_PREFIX}{encrypted}'


def decrypt_value(value):
    if not value:
        return value
    if not is_encrypted_value(value):
        return value

    cipher = _get_cipher()
    if cipher is None:
        return value

    payload = value[len(ENCRYPTED_PREFIX):]
    try:
        return cipher.decrypt(payload.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return value
