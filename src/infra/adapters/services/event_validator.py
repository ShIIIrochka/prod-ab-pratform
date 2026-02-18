from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError, create_model

from src.application.ports.event_validator import EventValidatorPort
from src.domain.value_objects.validation import (
    ValidationFieldError,
    ValidationResult,
)


# Маппинг строковых имён типов (из required_params) -> python-тип для Pydantic
_TYPE_MAP: dict[str, type] = {
    "string": str,
    "str": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
}


def _resolve_type(type_str: str) -> type | None:
    return _TYPE_MAP.get(type_str.lower())


class PydanticEventValidator(EventValidatorPort):
    """Реализация EventValidatorPort через Pydantic.

    Динамически строит Pydantic-модель по схеме required_params типа события.
    Кэширует модели по схеме для производительности.
    Use case ничего не знает о Pydantic — детали инкапсулированы здесь.
    """

    def __init__(self) -> None:
        # Кэш: frozenset(items) -> Pydantic-модель
        self._model_cache: dict[frozenset, type[BaseModel]] = {}

    def _build_model(self, required_params: dict[str, Any]) -> type[BaseModel]:
        """Построить (или взять из кэша) Pydantic-модель по схеме параметров."""
        cache_key = frozenset(required_params.items())
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        field_definitions: dict[str, Any] = {}
        for param_name, type_str in required_params.items():
            python_type = _resolve_type(str(type_str))
            # Обязательное поле (без default)
            field_definitions[param_name] = (python_type, ...)

        model = create_model(
            "EventPropsModel",
            **field_definitions,
            # Дополнительные поля разрешены (props могут содержать больше данных)
            model_config={"extra": "allow"},  # type: ignore[call-arg]
        )
        self._model_cache[cache_key] = model
        return model

    def validate(
        self,
        required_params: dict[str, Any],
        props: dict[str, Any],
    ) -> ValidationResult:
        """Валидировать props по схеме required_params.

        Args:
            required_params: Схема вида {"field_name": "type_str"}.
            props: Реальные параметры события.

        Returns:
            ValidationResult (domain value object).
        """
        if not required_params:
            return ValidationResult.ok(normalized_props=props)

        model_cls = self._build_model(required_params)

        try:
            instance = model_cls.model_validate(props)
            return ValidationResult.ok(normalized_props=instance.model_dump())
        except ValidationError as exc:
            errors = [
                ValidationFieldError(
                    field=".".join(str(loc) for loc in err["loc"]),
                    message=err["msg"],
                )
                for err in exc.errors()
            ]
            return ValidationResult.fail(errors)
