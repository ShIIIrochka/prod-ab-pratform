from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Security, status

from src.application.dto.metric import (
    MetricCreateRequest,
    MetricListResponse,
    MetricResponse,
)
from src.application.usecases.metrics.create import CreateMetricUseCase
from src.application.usecases.metrics.get import GetMetricUseCase
from src.application.usecases.metrics.list import ListMetricsUseCase
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import Container, require_roles
from src.presentation.rest.middlewares import AuthUser, JWTBackend


router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.post(
    "",
    response_model=MetricResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_metric(
    data: MetricCreateRequest,
    container: Container,
    _: Annotated[AuthUser, Depends(require_roles([UserRole.ADMIN]))],
) -> MetricResponse:
    use_case = container.resolve(CreateMetricUseCase)
    metric = await use_case.execute(
        key=data.key,
        name=data.name,
        calculation_rule=data.calculation_rule,
        requires_exposure=data.requires_exposure,
        description=data.description,
    )
    return MetricResponse.model_validate(metric)


@router.get("", response_model=MetricListResponse)
async def list_metrics(container: Container) -> MetricListResponse:
    use_case = container.resolve(ListMetricsUseCase)
    metrics = await use_case.execute()
    return MetricListResponse(
        metrics=[MetricResponse.model_validate(m) for m in metrics]
    )


@router.get("/{key}", response_model=MetricResponse)
async def get_metric(key: str, container: Container) -> MetricResponse:
    use_case = container.resolve(GetMetricUseCase)
    metric = await use_case.execute(key)
    return MetricResponse.model_validate(metric)
