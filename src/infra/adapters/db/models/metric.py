from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from src.domain.aggregates.metric import AggregationUnit, Metric


class MetricModel(Model):
    key = fields.CharField(
        max_length=255, pk=True, description="Metric key (primary identifier)"
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
    aggregation_unit = fields.CharField(
        max_length=10,
        default=AggregationUnit.EVENT.value,
        description="Aggregation unit: event or user",
    )

    class Meta:
        table = "metrics"

    def to_domain(self) -> Metric:
        return Metric(
            key=self.key,
            name=self.name,
            calculation_rule=self.calculation_rule,
            requires_exposure=self.requires_exposure,
            description=self.description,
            aggregation_unit=AggregationUnit(self.aggregation_unit),
        )

    @classmethod
    def from_domain(cls, metric: Metric) -> MetricModel:
        return cls(
            key=metric.key,
            name=metric.name,
            calculation_rule=metric.calculation_rule,
            requires_exposure=metric.requires_exposure,
            description=metric.description,
            aggregation_unit=metric.aggregation_unit.value,
        )
