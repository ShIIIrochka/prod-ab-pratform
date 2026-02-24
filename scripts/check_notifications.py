#!/usr/bin/env python3
"""
Check notifications flow: login, optional Slack connect, create experiment and launch
to trigger status notifications. Does not verify delivery (use Slack channel or mock).

Env: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD; optional SLACK_WEBHOOK_URL for connect.
Exit: 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys

import requests


BASE_URL = os.environ.get("BASE_URL", "http://localhost:80").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin_pass")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

FLAG_KEY = "notif_check_flag"


def log(msg: str) -> None:
    print(f"[notif] {msg}")


def main() -> int:
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"

    log("Logging in...")
    r = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        log(f"Login failed: {r.status_code} {r.text}")
        return 1
    session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    if SLACK_WEBHOOK_URL:
        log("Connecting Slack channel...")
        r = session.post(
            f"{BASE_URL}/notifications/slack/connect",
            json={"name": "Jury Slack", "webhook_url": SLACK_WEBHOOK_URL},
            timeout=10,
        )
        if r.status_code not in (200, 201):
            log(f"Slack connect failed: {r.status_code} {r.text}")
            return 1
        log("Slack connected (webhook masked in response).")
    else:
        log("SLACK_WEBHOOK_URL not set; skipping Slack connect.")

    # Ensure flag exists
    r = session.post(
        f"{BASE_URL}/feature-flags",
        json={
            "key": FLAG_KEY,
            "value_type": "string",
            "default_value": "off",
        },
        timeout=10,
    )
    if r.status_code not in (201, 400):
        log(f"Feature flag failed: {r.status_code} {r.text}")
        return 1

    log("Creating experiment...")
    r = session.post(
        f"{BASE_URL}/experiments",
        json={
            "flag_key": FLAG_KEY,
            "name": "Notification check experiment",
            "audience_fraction": 0.2,
            "variants": [
                {
                    "name": "control",
                    "value": "off",
                    "weight": 0.1,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": "on",
                    "weight": 0.1,
                    "is_control": False,
                },
            ],
        },
        timeout=10,
    )
    if r.status_code != 201:
        log(f"Experiment create failed: {r.status_code} {r.text}")
        return 1
    exp_id = r.json()["id"]

    for step, path, payload in [
        ("send-to-review", "send-to-review", {}),
        ("approve", "approve", {"comment": "ok"}),
        ("launch", "launch", {}),
    ]:
        log(f"Experiment {step}...")
        r = session.post(
            f"{BASE_URL}/experiments/{exp_id}/{path}",
            json=payload,
            timeout=10,
        )
        if r.status_code != 200:
            log(f"Experiment {step} failed: {r.status_code} {r.text}")
            return 1

    log(
        "Notifications check OK: experiment launched; events emitted to queue (Celery worker must be running for delivery)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
