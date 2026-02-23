from __future__ import annotations

import logging
import ssl

from opensearchpy import AsyncOpenSearch


logger = logging.getLogger(__name__)

LEARNINGS_INDEX_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
    },
    "mappings": {
        "properties": {
            "experiment_id": {"type": "keyword"},
            "name": {"type": "text"},
            "search_text": {"type": "text"},
            "flag_key": {"type": "keyword"},
            "owner_id": {"type": "keyword"},
            "outcome": {"type": "keyword"},
            "target_metric_key": {"type": "keyword"},
            "metric_keys": {"type": "keyword"},
            "guardrail_metric_keys": {"type": "keyword"},
            "targeting_rule": {"type": "text"},
            "comment": {"type": "text"},
            "completed_at": {"type": "date"},
            "created_at": {"type": "date"},
        },
    },
}


class OpenSearch:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        index_name: str,
    ) -> None:
        self._hosts = [{"host": host, "port": port}]
        self._auth = (username, password)
        self._index_name = index_name
        self._client: AsyncOpenSearch | None = None

    @property
    def client(self) -> AsyncOpenSearch | None:
        return self._client

    @property
    def index_name(self) -> str:
        return self._index_name

    def _create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def connect(self) -> None:
        try:
            self._create_ssl_context()
            self._client = AsyncOpenSearch(
                hosts=self._hosts,
                use_ssl=True,
                verify_certs=False,
            )
            exists = await self._client.indices.exists(index=self._index_name)
            if not exists:
                await self._client.indices.create(
                    index=self._index_name,
                    body=LEARNINGS_INDEX_MAPPING,
                )
        except Exception as e:
            logger.warning(
                "OpenSearch connect failed (learnings search disabled): %s",
                e,
            )
            self._client = None

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
