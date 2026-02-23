"""Minimal mock HTTP webhook server for integration and demo tests.

Usage in tests::

    async with MockWebhookServer() as server:
        # server.url  -> e.g. "http://127.0.0.1:8765"
        # ... configure channel config to point here ...
        # ... trigger notifications ...
        assert len(server.received_requests) == 1
        payload = server.received_requests[0]["body"]

Demo usage (manual):
    Start the mock server standalone so you can trigger experiments and
    observe the HTTP webhook payloads in the terminal::

        python -m tests.e2e.mock_webhook_server

    Then set DEMO_WEBHOOK_URL=http://127.0.0.1:8765 in your .env to point
    your channel config at this server.
"""

from __future__ import annotations

import asyncio
import json
import logging


logger = logging.getLogger(__name__)


class MockWebhookServer:
    """Async context manager that runs a tiny HTTP webhook sink.

    Records all POST requests as dicts with keys ``body`` and ``headers``.
    Responds 200 OK to every request.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        # port=0 lets the OS pick a free port
        self._port = port
        self._server: asyncio.Server | None = None
        self.received_requests: list[dict] = []

    @property
    def url(self) -> str:
        assert self._server is not None, "Server not started"
        actual_port = self._server.sockets[0].getsockname()[1]
        return f"http://{self._host}:{actual_port}"

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await reader.readline()
            headers: dict[str, str] = {}
            content_length = 0
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                if b":" in line:
                    name, _, value = line.decode().partition(":")
                    headers[name.strip().lower()] = value.strip()
                    if name.strip().lower() == "content-length":
                        content_length = int(value.strip())

            body_bytes = (
                await reader.read(content_length) if content_length else b""
            )
            body_text = body_bytes.decode("utf-8", errors="replace")

            try:
                parsed_body = json.loads(body_text)
            except (json.JSONDecodeError, ValueError):
                parsed_body = body_text

            self.received_requests.append(
                {
                    "request_line": request_line.decode().strip(),
                    "headers": headers,
                    "body": parsed_body,
                    "body_raw": body_text,
                }
            )
            logger.info(
                "MockWebhookServer received: %s  body=%r",
                request_line.decode().strip(),
                body_text[:200],
            )

            response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            writer.write(response)
            await writer.drain()
        except Exception as exc:
            logger.debug("MockWebhookServer handler error: %s", exc)
        finally:
            writer.close()

    async def __aenter__(self) -> MockWebhookServer:
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()


# ---------------------------------------------------------------------------
# Standalone demo entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

    async def _run() -> None:
        server = MockWebhookServer(port=port)
        async with server:
            real_url = server.url
            print(f"\n✅ Mock webhook server listening at: {real_url}")
            print(f"   → set DEMO_WEBHOOK_URL={real_url} in your .env\n")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down.")

    asyncio.run(_run())
