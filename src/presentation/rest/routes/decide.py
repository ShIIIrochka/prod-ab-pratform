from __future__ import annotations

from fastapi import APIRouter

from src.application.dto.decide import (
    DecideRequest,
    DecideResponse,
    DecisionResponse,
)
from src.application.usecases.decide import DecideUseCase
from src.presentation.rest.dependencies import Container


router = APIRouter(tags=["Decide"])


@router.post("/decide", response_model=DecideResponse)
async def decide(
    data: DecideRequest,
    container: Container,
) -> DecideResponse:
    use_case = container.resolve(DecideUseCase)
    decisions_map = await use_case.execute(data)
    return DecideResponse(
        decisions={
            flag_key: DecisionResponse.model_validate(decision)
            for flag_key, decision in decisions_map.items()
        }
    )
