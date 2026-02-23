from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient


def _unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def now_unix(offset_seconds: int = 0) -> int:
    return _unix(datetime.now(UTC) + timedelta(seconds=offset_seconds))


async def ensure_feature_flag(
    client: AsyncClient,
    headers: dict,
    key: str,
    value_type: str = "string",
    default_value="off",
) -> None:
    r = await client.post(
        "/feature-flags",
        json={
            "key": key,
            "value_type": value_type,
            "default_value": default_value,
        },
        headers=headers,
    )
    assert r.status_code in (201, 400), r.text


async def ensure_event_type(
    client: AsyncClient,
    headers: dict,
    key: str,
    name: str,
    requires_exposure: bool = False,
) -> None:
    r = await client.post(
        "/event-types",
        json={
            "key": key,
            "name": name,
            "description": "",
            "required_params": {},
            "requires_exposure": requires_exposure,
        },
        headers=headers,
    )
    assert r.status_code in (201, 400), r.text


async def ensure_metric(
    client: AsyncClient,
    headers: dict,
    key: str,
    name: str,
    calculation_rule: str,
    aggregation_unit: str = "user",
) -> None:
    r = await client.post(
        "/metrics",
        json={
            "key": key,
            "name": name,
            "calculation_rule": calculation_rule,
            "aggregation_unit": aggregation_unit,
        },
        headers=headers,
    )
    assert r.status_code in (201, 400), r.text


async def create_and_launch_experiment(
    client: AsyncClient,
    headers: dict,
    flag_key: str,
    name: str,
    variants: list[dict] | None = None,
    target_metric_key: str | None = None,
    metric_keys: list[str] | None = None,
    guardrails: list[dict] | None = None,
    audience_fraction: float = 1.0,
) -> str:
    if variants is None:
        variants = [
            {
                "name": "control",
                "value": "off",
                "weight": 0.5,
                "is_control": True,
            },
            {
                "name": "treatment",
                "value": "on",
                "weight": 0.5,
                "is_control": False,
            },
        ]

    body: dict = {
        "flag_key": flag_key,
        "name": name,
        "audience_fraction": audience_fraction,
        "variants": variants,
    }
    if target_metric_key:
        body["target_metric_key"] = target_metric_key
    if metric_keys:
        body["metric_keys"] = metric_keys
    if guardrails:
        body["guardrails"] = guardrails

    r = await client.post("/experiments", json=body, headers=headers)
    assert r.status_code == 201, r.text
    exp_id = r.json()["id"]

    r = await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=headers
    )
    assert r.status_code == 200, r.text

    r = await client.post(
        f"/experiments/{exp_id}/approve",
        json={"comment": "ok"},
        headers=headers,
    )
    assert r.status_code == 200, r.text

    r = await client.post(f"/experiments/{exp_id}/launch", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"

    return exp_id


async def ensure_subject_user(
    client: AsyncClient, headers: dict, user_id: str
) -> None:
    from src.infra.adapters.db.models.user import UserModel

    await UserModel.get_or_create(
        id=user_id,
        defaults={
            "email": f"{user_id}@test.example",
            "password": "hashed_stub",
            "role": "viewer",
        },
    )
