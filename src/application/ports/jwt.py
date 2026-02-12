from abc import ABC, abstractmethod

from domain.value_objects.jwt import JWTPayload


class JWTPort(ABC):
    @abstractmethod
    async def create(self, payload: JWTPayload) -> str:
        raise NotImplementedError

    async def verify(self, token: str) -> JWTPayload:
        raise NotImplementedError
