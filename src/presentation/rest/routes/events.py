from __future__ import annotations

from fastapi import APIRouter, status

from src.application.dto.events import (
    EventErrorDetail,
    SendEventsRequest,
    SendEventsResponse,
)
from src.application.usecases.events.send import SendEventsUseCase
from src.domain.value_objects.event_processing import EventsBatchResult
from src.presentation.rest.dependencies import Container


router = APIRouter(tags=["Events"])


def _to_response(result: EventsBatchResult) -> SendEventsResponse:
    """Конвертировать domain value object в Pydantic HTTP-ответ."""
    return SendEventsResponse(
        accepted=result.accepted,
        duplicates=result.duplicates,
        rejected=result.rejected,
        errors=[
            EventErrorDetail(
                index=err.index,
                event_type_key=err.event_type_key,
                reason=err.reason,
            )
            for err in result.errors
        ],
    )


@router.post(
    "/events", response_model=SendEventsResponse, status_code=status.HTTP_200_OK
)
async def send_events(
    data: SendEventsRequest,
    container: Container,
) -> SendEventsResponse:
    use_case = container.resolve(SendEventsUseCase)
    result: EventsBatchResult = await use_case.execute(data)
    return _to_response(result)
