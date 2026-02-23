"""Unit tests for NotificationRule.matches() filtering logic."""

from __future__ import annotations

from uuid import uuid4

from src.domain.entities.notification_rule import NotificationRule
from src.domain.value_objects.notification_event_type import (
    NotificationEventType,
)


def _make_rule(**kwargs) -> NotificationRule:
    defaults = {
        "id": uuid4(),
        "event_type": "experiment.launched",
        "channel_config_id": uuid4(),
        "enabled": True,
        "rate_limit_seconds": 0,
    }
    defaults.update(kwargs)
    return NotificationRule(**defaults)


def test_rule_matches_exact_event_type() -> None:
    rule = _make_rule(event_type="experiment.launched")
    assert rule.matches("experiment.launched", uuid4(), {}) is True


def test_rule_does_not_match_wrong_event_type() -> None:
    rule = _make_rule(event_type="experiment.launched")
    assert rule.matches("experiment.paused", uuid4(), {}) is False


def test_rule_with_wildcard_event_type() -> None:
    rule = _make_rule(event_type="*")
    assert rule.matches("experiment.launched", uuid4(), {}) is True
    assert rule.matches("guardrail.triggered", uuid4(), {}) is True


def test_disabled_rule_never_matches() -> None:
    rule = _make_rule(enabled=False)
    assert rule.matches("experiment.launched", uuid4(), {}) is False


def test_rule_with_experiment_id_filter() -> None:
    target_id = uuid4()
    rule = _make_rule(event_type="*", experiment_id=target_id)

    assert rule.matches("experiment.launched", target_id, {}) is True
    assert rule.matches("experiment.launched", uuid4(), {}) is False


def test_rule_with_flag_key_filter() -> None:
    rule = _make_rule(event_type="*", flag_key="my_flag")

    assert (
        rule.matches("experiment.launched", uuid4(), {"flag_key": "my_flag"})
        is True
    )
    assert (
        rule.matches("experiment.launched", uuid4(), {"flag_key": "other_flag"})
        is False
    )
    assert rule.matches("experiment.launched", uuid4(), {}) is False


def test_rule_with_owner_id_filter() -> None:
    rule = _make_rule(event_type="*", owner_id="user-123")

    assert (
        rule.matches("experiment.launched", uuid4(), {"owner_id": "user-123"})
        is True
    )
    assert (
        rule.matches("experiment.launched", uuid4(), {"owner_id": "user-456"})
        is False
    )


def test_rule_with_metric_key_filter() -> None:
    rule = _make_rule(
        event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
        metric_key="crash_rate",
    )
    entity_id = uuid4()
    assert (
        rule.matches(
            NotificationEventType.GUARDRAIL_TRIGGERED,
            entity_id,
            {"metric_key": "crash_rate"},
        )
        is True
    )
    assert (
        rule.matches(
            NotificationEventType.GUARDRAIL_TRIGGERED,
            entity_id,
            {"metric_key": "latency"},
        )
        is False
    )


def test_rule_with_multiple_filters_all_must_match() -> None:
    target_id = uuid4()
    rule = _make_rule(
        event_type="*",
        experiment_id=target_id,
        flag_key="specific_flag",
    )
    # Both conditions met
    assert (
        rule.matches(
            "experiment.launched", target_id, {"flag_key": "specific_flag"}
        )
        is True
    )
    # Only one condition met
    assert (
        rule.matches(
            "experiment.launched", target_id, {"flag_key": "wrong_flag"}
        )
        is False
    )
    assert (
        rule.matches(
            "experiment.launched", uuid4(), {"flag_key": "specific_flag"}
        )
        is False
    )
