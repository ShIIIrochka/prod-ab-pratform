from abc import ABC, abstractmethod


class UnitOfWorkPort(ABC):
    @abstractmethod
    async def __aenter__(self):
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError
