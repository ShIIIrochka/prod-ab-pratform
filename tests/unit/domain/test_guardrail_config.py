"""Unit tests for GuardrailConfig with metric_key."""

from __future__ import annotations

import pytest

from src.domain.entities.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)


def test_guardrail_config_uses_metric_key():
    """GuardrailConfig должен принимать metric_key: str."""
    config = GuardrailConfig(
        metric_key="error_rate",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )
    assert config.metric_key == "error_rate"


def test_guardrail_config_negative_window_raises():
    """observation_window_minutes <= 0 должен вызывать ValueError."""
    with pytest.raises(ValueError, match="Observation window must be positive"):
        GuardrailConfig(
            metric_key="error_rate",
            threshold=0.05,
            observation_window_minutes=0,
            action=GuardrailAction.PAUSE,
        )


def test_guardrail_config_rollback_action():
    """GuardrailConfig с ROLLBACK_TO_CONTROL сохраняет действие."""
    config = GuardrailConfig(
        metric_key="p95_latency",
        threshold=200.0,
        observation_window_minutes=5,
        action=GuardrailAction.ROLLBACK_TO_CONTROL,
    )
    assert config.action == GuardrailAction.ROLLBACK_TO_CONTROL


def test_guardrail_config_has_unique_id():
    """Each GuardrailConfig instance has a unique UUID id."""
    from uuid import UUID

    c1 = GuardrailConfig(
        metric_key="error_rate",
        threshold=0.1,
        observation_window_minutes=15,
        action=GuardrailAction.PAUSE,
    )
    c2 = GuardrailConfig(
        metric_key="error_rate",
        threshold=0.1,
        observation_window_minutes=15,
        action=GuardrailAction.PAUSE,
    )
    assert isinstance(c1.id, UUID)
    assert c1.id != c2.id
