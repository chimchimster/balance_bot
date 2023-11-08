import asyncio
import logging
import unittest
from unittest.mock import Mock

import sqlalchemy.exc
from aiogram.types import Message
from sqlalchemy.schema import CreateSchema
from sqlalchemy.sql.ddl import DropSchema

from database.session import AsyncSessionLocal
from database.models import *
from database.engine import postgres_engine
from database.handlers.utils.redis_client import connect_redis_url
from middlewares.utils.state import check_auth_state
from signals.signals import Signal


class TestAuthState(unittest.IsolatedAsyncioTestCase):

    def setUp(self):

        self.meta = Base()
        self.lock = asyncio.Lock()
        self.loop = asyncio.new_event_loop()

        self.tg_user_id = 1234

        async def create_schemas(lock):
            async with lock:
                async with AsyncSessionLocal() as session:
                    async with session.begin() as transaction:
                        try:
                            await session.execute(CreateSchema('auth', if_not_exists=True))
                            await session.execute(CreateSchema('commerce', if_not_exists=True))
                            await transaction.commit()
                        except sqlalchemy.exc.SQLAlchemyError as sql_err:
                            logging.getLogger(__name__).error(str(sql_err))
                            await transaction.rollback()
                        except Exception as e:
                            logging.getLogger(__name__).error(str(e))

        async def create_tables(lock):
            async with lock:
                async with postgres_engine.engine.begin() as conn:
                    await conn.run_sync(self.meta.metadata.create_all)

        self.loop.run_until_complete(create_schemas(self.lock))
        self.loop.run_until_complete(create_tables(self.lock))

    async def asyncSetUp(self):

        self.r_con = await connect_redis_url()

    def test001_check_redis_connection(self):
        async def check_redis_connection():
            self.assertIsNotNone(self.r_con)

        self.loop.run_until_complete(check_redis_connection())

    def test002_check_auth_state(self):
        message = Mock()
        message.from_user.id = self.tg_user_id

        async def check_auth_state_registered(lock):
            nonlocal message

            async with lock:
                signal = await check_auth_state(message)
                self.assertEqual(signal, Signal.NOT_REGISTERED)

        async def check_auth_state_not_authenticated(lock):
            nonlocal message

            try:
                async with lock:
                    async with AsyncSessionLocal() as session:
                        async with session.begin() as transaction:
                            await Users.create_user(self.tg_user_id, 'Anakin', 'Skywalker', session)
                            await transaction.commit()
            except sqlalchemy.exc.SQLAlchemyError:
                await transaction.rollback()

            async with lock:
                signal = await check_auth_state(message)
                self.assertEqual(signal, Signal.NOT_AUTHENTICATED)

        async def check_auth_state_authenticated(lock):
            nonlocal message

            async with lock:
                signal = await check_auth_state(message)
                self.assertEqual(signal, Signal.AUTHENTICATED)

        self.loop.run_until_complete(check_auth_state_registered(self.lock))
        self.loop.run_until_complete(check_auth_state_not_authenticated(self.lock))
        self.loop.run_until_complete(check_auth_state_authenticated(self.lock))

    def tearDown(self):

        async def drop_down_tables():
            async with postgres_engine.engine.begin() as conn:
                await conn.run_sync(self.meta.metadata.drop_all, checkfirst=True)

        async def drop_schemas():
            async with AsyncSessionLocal() as session:
                async with session.begin() as transaction:
                    try:
                        await session.execute(DropSchema('auth'))
                        await session.execute(DropSchema('commerce'))
                        await transaction.commit()
                    except sqlalchemy.exc.SQLAlchemyError as sql_err:
                        logging.getLogger(__name__).error(str(sql_err))
                        await transaction.rollback()

        self.loop.run_until_complete(drop_down_tables())
        self.loop.run_until_complete(drop_schemas())


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuthState)
    unittest.TextTestRunner(failfast=False).run(suite)
