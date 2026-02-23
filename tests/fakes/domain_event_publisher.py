from src.application.ports.domain_events import HasDomainEvents
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.domain.events.experiment import (
    ExperimentStatusChanged,
    GuardrailTriggered,
)


class FakeDomainEventPublisher(DomainEventPublisher):
    """No-op publisher for tests that don't care about notifications."""

    def __init__(self) -> None:
        self.published: list = []

    async def publish(
        self, domain_event: ExperimentStatusChanged | GuardrailTriggered
    ) -> None:
        self.published.append(domain_event)

    async def publish_from(self, aggregate: HasDomainEvents) -> None:
        events = aggregate.pop_domain_events()
        self.published.extend(events)
