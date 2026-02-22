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
    "/events",
    response_model=SendEventsResponse,
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "exposure_event": {
                            "summary": "Single exposure event",
                            "value": {
                                "events": [
                                    {
                                        "event_type_key": "exposure",
                                        "decision_id": "550e8400-e29b-41d4-a716-446655440000",
                                        "timestamp": 1700000000,
                                        "props": {},
                                    }
                                ]
                            },
                        },
                        "batch_exposure_and_conversion": {
                            "summary": "Exposure + conversion batch",
                            "value": {
                                "events": [
                                    {
                                        "event_type_key": "exposure",
                                        "decision_id": "550e8400-e29b-41d4-a716-446655440000",
                                        "timestamp": 1700000000,
                                        "props": {"screen": "checkout"},
                                    },
                                    {
                                        "event_type_key": "conversion",
                                        "decision_id": "550e8400-e29b-41d4-a716-446655440000",
                                        "timestamp": 1700000060,
                                        "props": {"product_id": "book-123"},
                                    },
                                ]
                            },
                        },
                    }
                }
            }
        }
    },
)
async def send_events(
    data: SendEventsRequest,
    container: Container,
) -> SendEventsResponse:
    use_case = container.resolve(SendEventsUseCase)
    result: EventsBatchResult = await use_case.execute(data)
    return _to_response(result)
