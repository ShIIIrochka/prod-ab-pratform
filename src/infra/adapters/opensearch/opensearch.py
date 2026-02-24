import logging
import ssl

from opensearchpy import AIOHttpConnection, AsyncOpenSearch


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
            "flag_key": {"type": "keyword"},
            "name": {"type": "text"},
            "status": {"type": "keyword"},
            "version": {"type": "integer"},
            "audience_fraction": {"type": "float"},
            "variants": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "value": {"type": "text"},
                    "weight": {"type": "float"},
                    "is_control": {"type": "boolean"},
                },
            },
            "targeting_rule": {"type": "text"},
            "owner_id": {"type": "keyword"},
            "target_metric_key": {"type": "keyword"},
            "metric_keys": {"type": "keyword"},
            "guardrails": {
                "type": "nested",
                "properties": {
                    "id": {"type": "keyword"},
                    "metric_key": {"type": "keyword"},
                    "threshold": {"type": "float"},
                    "observation_window_minutes": {"type": "integer"},
                    "action": {"type": "keyword"},
                },
            },
            "completion": {
                "type": "object",
                "properties": {
                    "outcome": {"type": "keyword"},
                    "winner_variant_id": {"type": "keyword"},
                    "comment": {"type": "text"},
                    "completed_at": {"type": "date"},
                    "completed_by": {"type": "keyword"},
                },
            },
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "hypothesis": {"type": "text"},
            "context_and_segment": {"type": "text"},
            "links": {"type": "keyword"},
            "notes": {"type": "text"},
            "tags": {"type": "keyword"},
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
        self._client: AsyncOpenSearch

    @property
    def client(self) -> AsyncOpenSearch:
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
                http_auth=self._auth,
                use_ssl=True,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
                connection_class=AIOHttpConnection,
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

    async def disconnect(self) -> None:
        await self._client.close()
