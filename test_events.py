import json

import requests


BASE_URL = "http://0.0.0.0:8000"
TOKEN = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogImp3dCJ9.eyJqdGkiOiAiYTlkNzc1NDgtYzAxNy00MjMzLTk2OGYtNGJiNzAwMGY2NzcyIiwgImV4cCI6IDE3NzE0NDkwOTkuNjc1MDAxLCAiaWF0IjogMTc3MTM2MjY5OS42NzUwMTIsICJ1c2VyX2lkIjogIjQxODM3YjU2LTE0N2ItNDdiYi1iMjE3LTVmMTVhMGYzZDdhZSIsICJyb2xlIjogImFkbWluIn0.KQfg67rye3ANXMDMDcgsrrUrG94Jg3YO5zICMAZQET8"


def pretty(resp):
    try:
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception:
        return resp.text


def create_event_type():
    print("\n=== CREATE EVENT TYPE ===")

    payload = {
        "key": "button_clicked",
        "name": "Button Clicked",
        "requires_exposure": True,
        "required_params": {"screen": "string"},
    }

    resp = requests.post(
        f"{BASE_URL}/event-types",
        json=payload,
        headers={"Authorization": TOKEN},
    )
    print("STATUS:", resp.status_code)
    print(pretty(resp))


def send_valid_event(decision_id):
    print("\n=== SEND VALID EVENT ===")

    payload = {
        "events": [
            {
                "event_type_key": "button_clicke",
                "decision_id": decision_id,
                "timestamp": "2026-02-17T12:00:00Z",
                "props": {"screen": "checkout"},
                "subject_id": "41837b56-147b-47bb-b217-5f15a0f3d7ae",
            }
        ]
    }

    resp = requests.post(f"{BASE_URL}/events", json=payload)
    print("STATUS:", resp.status_code)
    print(pretty(resp))

    # return resp.json().get("event")


def send_duplicate_event(event_id, decision_id):
    print("\n=== SEND DUPLICATE EVENT ===")

    payload = {
        "events": [
            {
                "event_id": event_id,
                "event_type": "button_clicked",
                "decision_id": decision_id,
                "timestamp": "2026-02-17T12:00:00Z",
                "props": {"screen": "checkout"},
            }
        ]
    }

    resp = requests.post(f"{BASE_URL}/events/batch", json=payload)
    print("STATUS:", resp.status_code)
    print(pretty(resp))


def send_invalid_event():
    print("\n=== SEND INVALID EVENT (missing required prop) ===")

    payload = {
        "events": [
            {
                "event_type_key": "button_clicked",
                "decision_id": "fake-decision",
                "timestamp": "2026-02-17T12:00:00Z",
                "props": {
                    # missing "screen"
                },
            }
        ]
    }

    resp = requests.post(f"{BASE_URL}/events", json=payload)
    print("STATUS:", resp.status_code)
    print(pretty(resp))


if __name__ == "__main__":
    # 1️⃣ создаём тип события
    # create_event_type()

    # 2️⃣ decision_id — подставь реальный из Decide API
    decision_id = "5a231b87-ce59-4139-ae05-1c6bc9232243"

    # 3️⃣ валидное событие
    event_id = send_valid_event(decision_id)

    # 4️⃣ дубликат
    # send_duplicate_event(event_id, decision_id)

    # 5️⃣ невалидное событие
    # send_invalid_event()
