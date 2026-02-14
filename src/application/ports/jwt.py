from abc import ABC, abstractmethod
from typing import Literal

from domain.value_objects.jwt import JWTPayload


class JWTPort(ABC):
    @abstractmethod
    async def create(
        self, token_type: Literal["access", "refresh"], payload: JWTPayload
    ) -> str:
        raise NotImplementedError

    async def verify(self, token: str) -> JWTPayload:
        raise NotImplementedError
