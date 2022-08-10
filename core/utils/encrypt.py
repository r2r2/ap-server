import random
import string
from typing import Iterable
import hashlib


def encrypt_password(passw: str, salt_len: int = 10) -> Iterable[str]:
    salt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=salt_len))
    crypted_pass = hashlib.sha256((passw + salt).encode("utf-8")).hexdigest()
    return crypted_pass, salt


def verify_password(raw_pass: str, db_pass: str, salt: str):
    crypted_pass = hashlib.sha256((raw_pass + salt).encode("utf-8")).hexdigest()
    return db_pass == crypted_pass
