from __future__ import annotations

import httpx
import pytest

from src.infra.adapters.channels.slack_webhook_channel import (
    SlackWebhookChannel,
)
from src.infra.adapters.channels.telegram_webhook_channel import (
    TelegramWebhookChannel,
)


pytestmark = pytest.mark.asyncio


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, status_code: int = 200, body: bytes = b"ok") -> None:
        self.status_code = status_code
        self.body = body
        self.requests: list[httpx.Request] = []

    async def handle_async_request(
        self, request: httpx.Request
    ) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status_code, content=self.body)


async def test_slack_sends_correct_payload(monkeypatch) -> None:
    transport = _MockTransport(200)

    async def _patched_client(*args, **kwargs):
        class Ctx:
            async def __aenter__(self_inner):
                return httpx.AsyncClient(transport=transport)

            async def __aexit__(self_inner, *a):
                pass

        return Ctx()

    import src.infra.adapters.channels.slack_webhook_channel as slack_mod

    # original = slack_mod.httpx.AsyncClient

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(slack_mod.httpx, "AsyncClient", PatchedClient)

    channel = SlackWebhookChannel()
    await channel.send("Hello Slack!", "https://hooks.slack.com/test")

    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req.method == "POST"
    assert b"Hello Slack!" in req.content


async def test_telegram_sends_correct_payload(monkeypatch) -> None:
    transport = _MockTransport(200)

    import src.infra.adapters.channels.telegram_webhook_channel as tg_mod

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(tg_mod.httpx, "AsyncClient", PatchedClient)

    channel = TelegramWebhookChannel()
    await channel.send(
        "Hello Telegram!",
        "https://api.telegram.org/botTOKEN/sendMessage?chat_id=123",
    )

    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert b"Hello Telegram!" in req.content


async def test_slack_raises_on_non_2xx(monkeypatch) -> None:
    transport = _MockTransport(500, b"Internal Server Error")

    import src.infra.adapters.channels.slack_webhook_channel as slack_mod

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(slack_mod.httpx, "AsyncClient", PatchedClient)

    channel = SlackWebhookChannel()
    with pytest.raises(httpx.HTTPStatusError):
        await channel.send("Test", "https://hooks.slack.com/test")


async def test_telegram_raises_on_non_2xx(monkeypatch) -> None:
    transport = _MockTransport(429, b"Too Many Requests")

    import src.infra.adapters.channels.telegram_webhook_channel as tg_mod

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(tg_mod.httpx, "AsyncClient", PatchedClient)

    channel = TelegramWebhookChannel()
    with pytest.raises(httpx.HTTPStatusError):
        await channel.send(
            "Test",
            "https://api.telegram.org/botTOKEN/sendMessage?chat_id=123",
        )
