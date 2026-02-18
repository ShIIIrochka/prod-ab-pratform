# from __future__ import annotations

# from datetime import datetime, timedelta

# from src.domain.aggregates.event import AttributionStatus, Event
# from src.domain.aggregates.event_type import EventType


# EXPOSURE_EVENT_TYPE = "exposure"
# ATTRIBUTION_WINDOW_DAYS = 7


# def check_exposure_exists(
#     exposure_events: list[Event],
#     target_event: Event,
# ) -> bool:
#     for event in exposure_events:
#         if event.event_type_key == EXPOSURE_EVENT_TYPE:
#             time_diff = target_event.timestamp - event.timestamp
#             if time_diff >= timedelta(0) and time_diff <= timedelta(
#                 days=ATTRIBUTION_WINDOW_DAYS
#             ):
#                 return True
#     return False


# def is_attribution_window_expired(
#     event: Event,
#     current_time: datetime,
# ) -> bool:
#     time_diff = current_time - event.timestamp
#     return time_diff > timedelta(days=ATTRIBUTION_WINDOW_DAYS)


# def determine_attribution_status(
#     event: Event,
#     requires_exposure: bool,
#     exposure_events: list[Event],
#     current_time: datetime,
# ) -> AttributionStatus:
#     # Exposure события атрибутируются всегда
#     if event.event_type_key == EXPOSURE_EVENT_TYPE:
#         return AttributionStatus.ATTRIBUTED

#     # Если exposure не требуется, атрибутируем
#     if not requires_exposure:
#         return AttributionStatus.ATTRIBUTED

#     # Если требуется exposure, проверяем его наличие
#     if check_exposure_exists(exposure_events, event):
#         return AttributionStatus.ATTRIBUTED

#     # Если окно истекло, отклоняем
#     if is_attribution_window_expired(event, current_time):
#         return AttributionStatus.REJECTED

#     # Иначе ждем exposure
#     return AttributionStatus.PENDING


# def recalculate_attribution_for_events(
#     events: list[Event],
#     event_types_map: dict[str, EventType],
#     exposure_events: list[Event],
#     current_time: datetime,
# ) -> dict[str, AttributionStatus]:
#     """Пересчитывает статус атрибуции для группы событий.

#     Args:
#         events: Список событий для пересчета
#         event_types_map: Маппинг event_type_key -> EventType
#         exposure_events: Список exposure событий
#         current_time: Текущее время

#     Returns:
#         Словарь {event_id: новый_статус}
#     """
#     result = {}

#     for event in events:
#         event_type = event_types_map.get(event.event_type_key)
#         if event_type is None:
#             # Тип не найден - пропускаем
#             continue

#         new_status = determine_attribution_status(
#             event,
#             event_type.requires_exposure,
#             exposure_events,
#             current_time,
#         )

#         result[event.id] = new_status

#     return result


# def should_attribute_event(
#     event: Event,
#     requires_exposure: bool,
#     events_by_decision: list[Event],
# ) -> bool:
#     """Legacy функция для обратной совместимости.

#     Deprecated: используйте determine_attribution_status вместо этого.
#     """
#     # Exposure события атрибутируются всегда
#     if event.event_type_key == EXPOSURE_EVENT_TYPE:
#         return True

#     # Если exposure не требуется, атрибутируем
#     if not requires_exposure:
#         return True

#     # Если требуется exposure, проверяем его наличие
#     return check_exposure_exists(events_by_decision, event)
