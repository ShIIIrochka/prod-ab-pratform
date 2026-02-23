from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HasDomainEvents(Protocol):
    """Any aggregate that accumulates domain events and can flush them."""

    def pop_domain_events(self) -> list: ...
