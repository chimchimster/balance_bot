import asyncio
import unittest

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.models import *


class TestHandlers(unittest.IsolatedAsyncioTestCase):

    def setUp(self):

        self.meta = Base()

        self.engine = create_async_engine(
            url='sqlite+aiosqlite:///:memory',
        )

        self.new_user_first_name = 'chim'
        self.new_user_last_name = 'chimster'
        self.new_user_password = 'chimchimster'
        self.new_user_tg_id = 1550

    async def init_models(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def test_user_registration(self):

        loop = asyncio.get_running_loop()

        async with AsyncSession(self.engine) as async_session:
            async with async_session.begin():

                user_id = await Users.create_user(
                    tg_id=self.new_user_tg_id,
                    first_name=self.new_user_first_name,
                    last_name=self.new_user_last_name,
                    session=async_session,
                )
                self.assertNotEqual(user_id, None)
                await async_session.commit()

    def tearDown(self):

        import pathlib
        mem_mock_obj = pathlib.Path().glob('./:memory')
        pathlib.Path(next(mem_mock_obj)).unlink()
