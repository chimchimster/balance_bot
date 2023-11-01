import random
import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from database.engine import engine
from database.models.schemas.base import Base


class TestRealDatabase(unittest.IsolatedAsyncioTestCase):
    async def test_engine(self):

        async with engine.connect() as connection:

            self.assertNotEqual(connection, None)


class TestMockDatabase(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        import faker

        self.meta = Base()

        self.engine = create_async_engine(
            url='sqlite+aiosqlite:///:memory',
        )

        self.resource_count = resource_count = random.randint(10, 50)
        fake = faker.Faker()

        self.tg_ids = [item for item in range(resource_count)]
        self.first_names = [fake.name() for _ in range(resource_count)]
        self.last_names = [fake.name() for _ in range(resource_count)]

    async def test_tables_exist(self):

        async with self.engine.begin() as conn:

            await conn.run_sync(self.meta.metadata.create_all, checkfirst=True)

            query = text("""SELECT name FROM sqlite_schema WHERE type ='table' AND name NOT LIKE 'sqlite_%';""")
            result = await conn.execute(query)

            table_names = [row[0] for row in result.fetchall()]

            self.assertIn('users', table_names, 'Таблица users отсутствует в базе данных.')
            self.assertIn('addresses', table_names, 'Таблица addresses отсутствует в базе данных.')
            self.assertIn('credentials', table_names, 'Таблица credentials отсутствует в базе данных.')
            self.assertIn('items_images', table_names, 'Таблица items_images отсутствует в базе данных.')
            self.assertIn('items', table_names, 'Таблица items отсутствует в базе данных.')
            self.assertIn('images', table_names, 'Таблица images отсутствует в базе данных.')
            self.assertIn('item_meta', table_names, 'Таблица item_meta отсутствует в базе данных.')
            self.assertIn('brands', table_names, 'Таблица brands отсутствует в базе данных.')
            self.assertIn('order_item', table_names, 'Таблица order_item отсутствует в базе данных.')
            self.assertIn('orders', table_names, 'Таблица orders отсутствует в базе данных.')
            self.assertIn('deliveries', table_names, 'Таблица deliveries отсутствует в базе данных.')

    async def test_user_creation(self):

        import asyncio
        from sqlalchemy import insert

        async with self.engine.begin() as conn:

            await conn.run_sync(self.meta.metadata.create_all, checkfirst=True)

            users = self.meta.metadata.tables['users']

            insert_stmt = insert(users).values(
                [
                    {'tg_id': tg_id, 'first_name': first_name, 'last_name': last_name}
                    for tg_id, first_name, last_name in zip(self.tg_ids, self.first_names, self.last_names)
                ]
            ).returning(users.c.tg_id, users.c.first_name, users.c.last_name)

            chunked_iterator_result = await conn.execute(insert_stmt)

            users = [user_data for user_data in chunked_iterator_result.fetchall()]

            self.assertEqual(self.resource_count, len(users))

    def tearDown(self):

        import pathlib

        mem_mock_obj = pathlib.Path().glob('./:memory')
        pathlib.Path(next(mem_mock_obj)).unlink()


if __name__ == '__main__':
    suite_real = unittest.TestLoader().loadTestsFromTestCase(TestRealDatabase)
    suite_mock = unittest.TestLoader().loadTestsFromTestCase(TestMockDatabase)
    for suite in zip(suite_real, suite_mock):
        unittest.TextTestRunner(failfast=False).run(suite)
