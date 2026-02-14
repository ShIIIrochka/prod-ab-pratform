from jam.utils import (
    check_password,
    deserialize_hash,
    hash_password,
    serialize_hash,
)

from src.application.ports.password_hasher import PasswordHasherPort


class PasswordHasher(PasswordHasherPort):
    def hash(self, password: str) -> str:
        salt, hash_ = hash_password(password)
        return serialize_hash(salt_hex=salt, hash_hex=hash_)

    def verify(self, password: str, hashed_password: str) -> bool:
        salt, hash_ = deserialize_hash(hashed_password)
        return check_password(password=password, salt_hex=salt, hash_hex=hash_)
