from __future__ import annotations

from uuid import UUID

from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.domain.entities.notification_rule import NotificationRule
from src.infra.adapters.db.models.notification_rule import NotificationRuleModel


class NotificationRulesRepository(NotificationRulesRepositoryPort):
    async def save(self, rule: NotificationRule) -> None:
        existing = await NotificationRuleModel.get_or_none(id=rule.id)
        model = NotificationRuleModel.from_domain(rule)
        if existing:
            await model.save(force_update=True)
        else:
            await model.save()

    async def get_by_id(self, rule_id: UUID) -> NotificationRule | None:
        model = await NotificationRuleModel.get_or_none(id=rule_id)
        return model.to_domain() if model else None

    async def list_all(
        self, enabled_only: bool = False
    ) -> list[NotificationRule]:
        q = NotificationRuleModel.all()
        if enabled_only:
            q = q.filter(enabled=True)
        models = await q.order_by("created_at")
        return [m.to_domain() for m in models]

    async def get_matching(
        self,
        event_type: str,
        entity_id: UUID,
        payload: dict,
    ) -> list[NotificationRule]:
        """Fetch candidate rules from DB then filter in Python.

        DB filters on event_type and enabled; Python filters on optional scopes.
        This keeps SQL simple while supporting wildcard event_type "*".
        """
        models = (
            await NotificationRuleModel.filter(enabled=True)
            .filter(event_type__in=[event_type, "*"])
            .all()
        )
        result = []
        for m in models:
            rule = m.to_domain()
            if rule.matches(event_type, entity_id, payload):
                result.append(rule)
        return result

    async def delete(self, rule_id: UUID) -> None:
        await NotificationRuleModel.filter(id=rule_id).delete()
