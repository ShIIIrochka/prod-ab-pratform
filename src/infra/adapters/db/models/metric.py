from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.aggregates.metric import Metric


class MetricModel(Model):
    key = fields.CharField(
        pk=True, max_length=255, description="Metric key (unique identifier)"
    )
    name = fields.CharField(
        max_length=500, description="Human-readable metric name"
    )

    calculation_rule = fields.TextField(description="Metric calculation rule")

    requires_exposure = fields.BooleanField(
        default=False,
        description="Whether metric requires exposure event for attribution",
    )
    description = fields.TextField(null=True, description="Metric description")

    class Meta:
        table = "metrics"

    def to_domain(self) -> Metric:
        return Metric(
            key=self.key,
            name=self.name,
            calculation_rule=self.calculation_rule,
            requires_exposure=self.requires_exposure,
            description=self.description,
        )

    @classmethod
    def from_domain(cls, metric: Metric) -> MetricModel:
        return cls(
            key=metric.key,
            name=metric.name,
            calculation_rule=metric.calculation_rule,
            requires_exposure=metric.requires_exposure,
            description=metric.description,
        )
