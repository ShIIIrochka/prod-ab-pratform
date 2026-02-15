from typing import Literal

from jam.aio import Jam

from src.domain.value_objects.jwt import JWTPayload


class JWTAdapter:
    def __init__(self, access_exp: int, refresh_exp: int, jam_instance: Jam):
        self._access_exp = access_exp
        self._refresh_exp = refresh_exp
        self._jam_instance = jam_instance

    async def create(
        self, token_type: Literal["access", "refresh"], payload: JWTPayload
    ) -> str:
        exp: int = (
            self._access_exp if token_type == "access" else self._refresh_exp
        )
        payload_ = await self._jam_instance.jwt_make_payload(
            exp=exp, data=payload.__dict__
        )
        return await self._jam_instance.jwt_create_token(payload_)

    async def verify(self, token: str) -> JWTPayload:
        payload = await self._jam_instance.jwt_verify_token(
            token=token, check_exp=True, check_list=False
        )
        return JWTPayload(
            user_id=payload.get("user_id"),
            role=payload.get("role"),
        )
