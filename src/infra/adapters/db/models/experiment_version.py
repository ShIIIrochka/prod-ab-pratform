from __future__ import annotations

from tortoise import fields
from tortoise.fields import OnDelete
from tortoise.models import Model

from src.domain.value_objects.experiment_version import ExperimentVersion


class ExperimentVersionModel(Model):
    id = fields.UUIDField(pk=True, generate=True)
    experiment = fields.ForeignKeyField(
        "models.ExperimentModel",
        related_name="versions",
        on_delete=OnDelete.CASCADE,
    )
    version = fields.IntField()
    snapshot = fields.JSONField()
    changed_at = fields.DatetimeField(auto_now_add=True)
    changed_by = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "experiment_versions"
        unique_together = (("experiment_id", "version"),)
        indexes = [
            ("experiment_id",),
        ]

    def to_domain(self) -> ExperimentVersion:
        return ExperimentVersion(
            version=self.version,
            changed_at=self.changed_at,
            changed_by=self.changed_by,
            snapshot=self.snapshot,
        )
