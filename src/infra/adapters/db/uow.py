from tortoise.transactions import in_transaction

from application.ports.uow import UnitOfWorkPort


class UnitOfWork(UnitOfWorkPort):
    async def __aenter__(self):
        self._ctx = in_transaction()
        self.tx = await self._ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
