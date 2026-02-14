from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class MetricModel(Model):
    """Tortoise модель для каталога метрик.

    Соответствует domain.aggregates.metric.Metric
    """

    key = fields.CharField(
        pk=True, max_length=255, description="Metric key (unique identifier)"
    )
    name = fields.CharField(
        max_length=500, description="Human-readable metric name"
    )

    # Правило вычисления метрики (DSL или JSON с правилами агрегации)
    calculation_rule = fields.TextField(description="Metric calculation rule")

    requires_exposure = fields.BooleanField(
        default=False,
        description="Whether metric requires exposure event for attribution",
    )
    description = fields.TextField(null=True, description="Metric description")

    class Meta:
        table = "metrics"
