import asyncio
import logging
import unittest
from unittest.mock import Mock

import sqlalchemy.exc
from aiogram.types import Message

from database.session import AsyncSessionLocal
from database.models import *
from database.engine import postgres_engine
from database.handlers.utils.redis_client import connect_redis_url
from middlewares.utils.state import check_auth_state


class TestAuthState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):

        self.r_con = await connect_redis_url()
        self.loop = asyncio.new_event_loop()

        async with postgres_engine.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def test001_check_redis_connection(self):
        async def check_redis_connection():
            self.assertIsNotNone(self.r_con)

        self.loop.run_until_complete(check_redis_connection())

    def test002_check_auth_state(self):
        message_1 = Mock()
        message_1.text = 'Hello, world!'
        message_1.from_user.id = 1234

        async def check_auth_state_1():
            nonlocal message_1

            signal = await check_auth_state(message_1)
            print(signal)

        self.loop.run_until_complete(check_auth_state_1())

    def __del__(self):

        if not self.loop.is_running():
            self.loop.close()
        else:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuthState)
    unittest.TextTestRunner(failfast=False).run(suite)
