"""Formats notification messages for delivery to external channels.

The formatter produces a human-readable string from a NotificationEvent and
the matching NotificationRule. It is a pure function (no I/O) so it's trivial
to test in isolation.
"""

from src.domain.entities.notification_rule import NotificationRule
from src.domain.value_objects.notification_event import NotificationEvent
from src.domain.value_objects.notification_event_type import (
    NotificationEventType,
)


def format_notification_message(
    event: NotificationEvent, rule: NotificationRule
) -> str:
    """Return a formatted message string for this event/rule pair.

    If the rule carries a custom template, ``{key}`` placeholders are filled
    from the event payload (plus ``event_type``). Falls through to a built-in
    formatter on missing keys or absent template.
    """
    if rule.template:
        try:
            return rule.template.format(
                **event.payload, event_type=event.event_type
            )
        except KeyError:
            pass

    event_type = event.event_type
    entity_id = event.entity_id
    payload = event.payload

    if event_type == NotificationEventType.GUARDRAIL_TRIGGERED:
        return (
            f"🚨 *Guardrail triggered* on experiment `{entity_id}`\n"
            f"Metric: `{payload.get('metric_key')}` — "
            f"actual: `{payload.get('actual_value')}` > threshold: `{payload.get('threshold')}`\n"
            f"Action: `{payload.get('action')}`"
        )

    name = payload.get("experiment_name", str(entity_id))
    status = payload.get("status", event_type.split(".")[-1])
    extra_parts = []
    if payload.get("outcome"):
        extra_parts.append(f"Outcome: `{payload['outcome']}`")
    if payload.get("comment"):
        extra_parts.append(f"Comment: {payload['comment']}")

    lines = [
        f"📋 Experiment *{name}* status changed: `{status}`",
        f"Experiment ID: `{entity_id}`",
    ]
    lines.extend(extra_parts)
    return "\n".join(lines)
