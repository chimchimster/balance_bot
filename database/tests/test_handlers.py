import asyncio
import unittest

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.models import *


class TestHandlers(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):

        self.loop = asyncio.new_event_loop()

        # Fixtures
        self.user_first_name = 'chim'
        self.user_last_name = 'chimster'
        self.user_password = 'chimchimster1'
        self.user_tg_id = 1550

        # Database mocks
        self.meta = meta = Base()
        self.engine = engine = create_async_engine(
            url='sqlite+aiosqlite:///:memory',
        )
        self.async_session = AsyncSession(self.engine)

        async with engine.begin() as conn:
            await conn.run_sync(meta.metadata.create_all, checkfirst=True)

    def test001_user_creation(self):
        async def create_user():

            user_id = await Users.create_user(
                tg_id=self.user_tg_id,
                first_name=self.user_first_name,
                last_name=self.user_last_name,
                session=self.async_session,
            )

            await self.async_session.commit()

            return user_id

        u_id = self.loop.run_until_complete(create_user())

        self.assertNotEqual(u_id, None)

    def test002_get_user_id(self):
        async def get_user_id():

            user_id = await Users.get_user_id(
                self.user_tg_id,
                self.async_session,
            )

            await self.async_session.commit()

            return user_id

        u_id = self.loop.run_until_complete(get_user_id())

        self.assertNotEqual(u_id, None)

    def test003_update_user(self):

        async def update_user_first_name():

            await Users.update_user(
                self.user_tg_id,
                self.async_session,
                first_name='Johnny',
            )

            await self.async_session.commit()

            updated_first_name = await self.async_session.execute(
                select(Users.first_name).filter_by(tg_id=self.user_tg_id)
            )
            updated_first_name = updated_first_name.scalar_one_or_none()

            self.assertEqual(first='Johnny', second=updated_first_name)

        async def update_user_last_name():

            await Users.update_user(
                self.user_tg_id,
                self.async_session,
                last_name='The Monster',
            )

            await self.async_session.commit()

            updated_last_name = await self.async_session.execute(
                select(Users.last_name).filter_by(tg_id=self.user_tg_id)
            )
            updated_last_name = updated_last_name.scalar_one_or_none()

            self.assertEqual(first='The Monster', second=updated_last_name)

        self.loop.run_until_complete(update_user_first_name())
        self.loop.run_until_complete(update_user_last_name())

    def test004_set_user_credentials(self):

        async def set_user_password():

            user_id = await Users.get_user_id(tg_id=self.user_tg_id, session=self.async_session)

            credentials = Credentials(user_id=user_id)

            await credentials.set_password(self.user_password)

            self.async_session.add(credentials)

            passwords_matched = await credentials.check_password(self.user_password)

            self.assertTrue(passwords_matched)

        self.loop.run_until_complete(set_user_password())

    def test006_set_user_hash(self):
        async def set_user_hash():

            user_id = await Users.get_user_id(tg_id=self.user_tg_id, session=self.async_session)

            credentials = Credentials(user_id=user_id)

            await credentials.set_auth_hash()

            self.async_session.add(credentials)

            auth_hash = await self.async_session.execute(select(Credentials.auth_hash).filter_by(user_id=user_id))
            auth_hash = auth_hash.scalar_one_or_none()

            self.assertTrue(auth_hash)

        self.loop.run_until_complete(set_user_hash())

    def test005_set_user_address(self):

        async def set_user_address():

            user_id = await Users.get_user_id(tg_id=self.user_tg_id, session=self.async_session)

            address = await Addresses.set_address(
                user_id,
                'KZ',
                'Coruscant',
                'Anakin Skywalker Street',
                '104',
                '+79087643331',
                self.async_session,
            )

            self.assertEqual(type(address), int)

        self.loop.run_until_complete(set_user_address())

    def test999_tear_down_module(self):

        import pathlib

        mem_mock_obj = pathlib.Path().glob('./:memory')

        mem_mock_obj_name = next(mem_mock_obj)
        pathlib.Path(mem_mock_obj_name).unlink()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHandlers)
    runner = unittest.TextTestRunner()
    runner.run(suite)
