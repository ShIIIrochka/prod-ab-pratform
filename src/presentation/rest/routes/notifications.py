from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status

from src.application.dto.notifications import (
    ChannelConfigResponse,
    ConnectSlackRequest,
    ConnectTelegramRequest,
    CreateChannelConfigRequest,
    CreateNotificationRuleRequest,
    NotificationDeliveryResponse,
    NotificationRuleResponse,
    UpdateNotificationRuleRequest,
    mask_webhook_url_for_response,
)
from src.application.dto.user import UserResponse
from src.application.usecases import (
    ConnectSlackUseCase,
    ConnectTelegramUseCase,
    CreateChannelConfigUseCase,
    CreateNotificationRuleUseCase,
    DeleteChannelConfigUseCase,
    ListChannelConfigsUseCase,
    ListNotificationDeliveriesUseCase,
    ListNotificationRulesUseCase,
    UpdateNotificationRuleUseCase,
)
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)
from src.domain.value_objects.user_role import UserRole
from src.presentation.rest.dependencies import Container, require_roles
from src.presentation.rest.middlewares import JWTBackend


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Security(JWTBackend.auth_required)],
)


@router.post(
    "/channel-configs",
    response_model=ChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel_config(
    data: CreateChannelConfigRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> ChannelConfigResponse:
    use_case = container.resolve(CreateChannelConfigUseCase)
    config = await use_case.execute(
        type=data.type,
        name=data.name,
        webhook_url=data.webhook_url,
        enabled=data.enabled,
    )
    return ChannelConfigResponse.model_validate(config)


@router.post(
    "/telegram/connect",
    response_model=ChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_telegram(
    data: ConnectTelegramRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> ChannelConfigResponse:
    use_case = container.resolve(ConnectTelegramUseCase)
    config = await use_case.execute(
        name=data.name,
        bot_token=data.bot_token,
        chat_id=data.chat_id,
    )
    return ChannelConfigResponse(
        id=config.id,
        type=config.type,
        name=config.name,
        webhook_url=mask_webhook_url_for_response(
            config.webhook_url, NotificationChannelType.TELEGRAM
        ),
        enabled=config.enabled,
        created_at=config.created_at,
    )


@router.delete("/telegram/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_telegram(
    config_id: UUID,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> None:
    use_case = container.resolve(DeleteChannelConfigUseCase)
    await use_case.execute(
        config_id, expected_type=NotificationChannelType.TELEGRAM
    )


@router.post(
    "/slack/connect",
    response_model=ChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_slack(
    data: ConnectSlackRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> ChannelConfigResponse:
    use_case = container.resolve(ConnectSlackUseCase)
    config = await use_case.execute(
        name=data.name,
        webhook_url=data.webhook_url,
    )
    return ChannelConfigResponse(
        id=config.id,
        type=config.type,
        name=config.name,
        webhook_url=mask_webhook_url_for_response(
            config.webhook_url, NotificationChannelType.SLACK
        ),
        enabled=config.enabled,
        created_at=config.created_at,
    )


@router.delete("/slack/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_slack(
    config_id: UUID,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> None:
    use_case = container.resolve(DeleteChannelConfigUseCase)
    await use_case.execute(
        config_id, expected_type=NotificationChannelType.SLACK
    )


@router.get("/channel-configs", response_model=list[ChannelConfigResponse])
async def list_channel_configs(
    container: Container,
    enabled_only: bool = False,
) -> list[ChannelConfigResponse]:
    use_case = container.resolve(ListChannelConfigsUseCase)
    configs = await use_case.execute(enabled_only=enabled_only)
    return [ChannelConfigResponse.model_validate(c) for c in configs]


@router.post(
    "/rules",
    response_model=NotificationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_rule(
    data: CreateNotificationRuleRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> NotificationRuleResponse:
    use_case = container.resolve(CreateNotificationRuleUseCase)
    rule = await use_case.execute(
        event_type=data.event_type,
        channel_config_id=data.channel_config_id,
        enabled=data.enabled,
        experiment_id=data.experiment_id,
        flag_key=data.flag_key,
        owner_id=data.owner_id,
        metric_key=data.metric_key,
        severity=data.severity,
        rate_limit_seconds=data.rate_limit_seconds,
        template=data.template,
    )
    return NotificationRuleResponse.model_validate(rule)


@router.get("/rules", response_model=list[NotificationRuleResponse])
async def list_notification_rules(
    container: Container,
    enabled_only: bool = False,
) -> list[NotificationRuleResponse]:
    use_case = container.resolve(ListNotificationRulesUseCase)
    rules = await use_case.execute(enabled_only=enabled_only)
    return [NotificationRuleResponse.model_validate(r) for r in rules]


@router.patch("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    rule_id: UUID,
    data: UpdateNotificationRuleRequest,
    container: Container,
    _: Annotated[UserResponse, Depends(require_roles([UserRole.ADMIN]))],
) -> NotificationRuleResponse:
    use_case = container.resolve(UpdateNotificationRuleUseCase)
    rule = await use_case.execute(
        rule_id=rule_id,
        enabled=data.enabled,
        rate_limit_seconds=data.rate_limit_seconds,
        template=data.template,
    )
    return NotificationRuleResponse.model_validate(rule)


@router.get("/deliveries", response_model=list[NotificationDeliveryResponse])
async def list_deliveries(
    container: Container,
    event_id: UUID | None = None,
    limit: int = 100,
) -> list[NotificationDeliveryResponse]:
    use_case = container.resolve(ListNotificationDeliveriesUseCase)
    deliveries = await use_case.execute(event_id=event_id, limit=limit)
    return [NotificationDeliveryResponse.model_validate(d) for d in deliveries]
