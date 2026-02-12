from tortoise import Tortoise


class Database:
    def __init__(self, db_uri: str, modules: dict[str, list[str]]) -> None:
        self._db_uri = db_uri
        self._modules = modules

    async def connect(self) -> None:
        await Tortoise.init(
            db_url=self._db_uri,
            modules=self._modules,
        )
        await Tortoise.generate_schemas(safe=True)

    async def disconnect(self) -> None:
        await Tortoise.close_connections()
