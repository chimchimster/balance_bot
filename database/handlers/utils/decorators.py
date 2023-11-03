import functools
import sqlalchemy.exc
from typing import Coroutine, Awaitable, Any

from session import PostgresAsyncSession


async def execute_transaction(coro: Coroutine[Any, Awaitable]) -> Any:

    @functools.wraps(coro)
    async def wrapper(*args, **kwargs):
        async with PostgresAsyncSession() as session:
            async with session.begin() as transaction:

                try:
                    result = await coro(*args, **kwargs, session=session)
                except sqlalchemy.exc.SQLAlchemyError as exc:
                    transaction.rollback()
                    raise exc
                else:
                    await transaction.commit()
                    return result

    return wrapper
