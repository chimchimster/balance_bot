import asyncio
import time
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.models import *
from database.handlers.utils.redis_client import connect_redis_url


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

        self.redis_client = await connect_redis_url()

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

            await self.async_session.close()

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

            await self.async_session.close()

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

            await self.async_session.close()

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

            await self.async_session.close()

            self.assertEqual(first='The Monster', second=updated_last_name)

        self.loop.run_until_complete(update_user_first_name())
        self.loop.run_until_complete(update_user_last_name())

    def test004_set_user_initial_credentials(self):

        async def set_user_initial_credentials():

            user_id = await Users.get_user_id(tg_id=self.user_tg_id, session=self.async_session)

            credentials = Credentials(user_id=user_id)

            await credentials.set_password(self.user_password)
            await credentials.set_auth_hash()

            passwords_matched = await credentials.check_password(self.user_password)

            self.assertTrue(passwords_matched)

            self.async_session.add(credentials)
            await self.async_session.commit()

            password_hash = await self.async_session.execute(select(Credentials.password_hash).filter_by(user_id=user_id))
            password_hash = password_hash.scalar_one_or_none()

            self.assertNotEqual(password_hash, None)

            auth_hash = await self.async_session.execute(select(Credentials.auth_hash).filter_by(user_id=user_id))
            auth_hash = auth_hash.scalar_one_or_none()

            self.assertNotEqual(auth_hash, None)

            last_seen = await self.async_session.execute(select(Credentials.last_seen).filter_by(user_id=user_id))
            last_seen = last_seen.scalar_one_or_none()

            now = int(time.time())
            self.assertNotEqual(last_seen, None)
            self.assertAlmostEqual(last_seen, now, delta=1)

            u_id = await self.async_session.execute(
                select(Credentials.user_id).join(Users, Users.id == Credentials.user_id).filter(Users.id == user_id)
            )
            u_id = u_id.scalar_one_or_none()
            self.assertEqual(u_id, user_id)

            await self.async_session.close()

        self.loop.run_until_complete(set_user_initial_credentials())

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

            await self.async_session.commit()

            adr = await self.async_session.execute(
                select(Addresses).filter_by(user_id=user_id)
            )
            adr = adr.scalar_one_or_none()

            self.assertEqual(adr.country, 'KZ')
            self.assertEqual(adr.city, 'Coruscant')
            self.assertEqual(adr.street, 'Anakin Skywalker Street')
            self.assertEqual(adr.apartment, '104')
            self.assertEqual(adr.phone, '79087643331')

            u_id = await self.async_session.execute(
                select(Addresses.user_id).join(Users, Addresses.user_id == Users.id).
                filter(Users.id == user_id)
            )
            u_id = u_id.scalar_one_or_none()

            await self.async_session.close()

            self.assertEqual(u_id, user_id)

        self.loop.run_until_complete(set_user_address())

    def test006_redis_connection(self):

        async def redis_connection():
            response = await self.redis_client.ping()
            self.assertTrue(response)

        self.loop.run_until_complete(redis_connection())

    def test007_add_auth_hash_into_redis(self):

        async def add_auth_hash_into_redis():

            user_id = await self.async_session.execute(select(Users.id).filter_by(tg_id=self.user_tg_id))
            user_id = user_id.scalar()

            auth_hash = await self.async_session.execute(
                select(Credentials.user_id, Credentials.auth_hash, Credentials.last_seen).filter_by(user_id=user_id)
            )
            u_id, auth_hash, last_seen = auth_hash.fetchone()

            await self.redis_client.hset(f'auth_hash:{u_id}', mapping={
                'hash': auth_hash,
                'last_seen': last_seen,
            })

            key_exists = await self.redis_client.exists(f'auth_hash:{u_id}')

            self.assertTrue(key_exists)

            auth_get_hash = await self.redis_client.hget(f'auth_hash:{u_id}', 'hash')
            auth_get_last_seen = await self.redis_client.hget(f'auth_hash:{u_id}', 'last_seen')

            credentials = await self.async_session.execute(
                select(Credentials.auth_hash, Credentials.last_seen).filter_by(user_id=u_id)
            )
            user_auth_hash, user_last_seen = credentials.fetchone()

            self.assertEqual(auth_get_hash.decode('utf-8'), user_auth_hash)
            self.assertEqual(user_last_seen, int(auth_get_last_seen))

            await self.async_session.close()

        self.loop.run_until_complete(add_auth_hash_into_redis())

    async def close_session(self):

        await self.async_session.close()
        await self.engine.dispose()

    def test998_tear_down_module(self):

        self.loop.run_until_complete(self.close_session())

        import pathlib

        mem_mock_obj = pathlib.Path().glob('./:memory')

        mem_mock_obj_name = next(mem_mock_obj)
        pathlib.Path(mem_mock_obj_name).unlink()

    def __del__(self):

        if not self.loop.is_running():
            self.loop.close()
        else:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHandlers)
    runner = unittest.TextTestRunner()
    runner.run(suite)
