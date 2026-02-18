from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EventProcessingError:
    """Ошибка обработки одного события в пачке.

    Value object: описывает причину отклонения события по его позиции в пачке.
    """

    index: int
    event_type_key: str
    reason: str


@dataclass(frozen=True)
class EventsBatchResult:
    """Результат обработки пачки событий.

    Domain value object, возвращаемый use case.
    Не содержит Pydantic — преобразование в HTTP-ответ выполняется
    на уровне presentation.
    """

    accepted: int
    duplicates: int
    rejected: int
    errors: tuple[EventProcessingError, ...] = field(default_factory=tuple)

    @classmethod
    def build(
        cls,
        accepted: int,
        duplicates: int,
        rejected: int,
        errors: list[EventProcessingError],
    ) -> EventsBatchResult:
        return cls(
            accepted=accepted,
            duplicates=duplicates,
            rejected=rejected,
            errors=tuple(errors),
        )
