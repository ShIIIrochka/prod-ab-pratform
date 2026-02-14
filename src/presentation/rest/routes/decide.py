from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from application.dto.decide import DecideRequest, DecideResponse
from application.usecases.decide import DecideUseCase
from presentation.rest.dependencies import Container


router = APIRouter(tags=["Decide"])


@router.post("/decide", response_model=DecideResponse)
async def decide(
    data: DecideRequest,
    container: Container,
) -> DecideResponse:
    try:
        use_case = container.resolve(DecideUseCase)
        response = await use_case.execute(data)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
