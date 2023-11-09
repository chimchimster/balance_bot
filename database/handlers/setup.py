import logging
import sqlalchemy.exc

from sqlalchemy.sql.ddl import CreateSchema


from database.models import *
from database.engine import postgres_engine
from database.handlers.utils.session import PostgresAsyncSession


async def setup_database():

    async with PostgresAsyncSession() as session:
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

    try:
        async with postgres_engine.engine.begin() as con:
            await con.run_sync(Base.metadata.create_all)
    except sqlalchemy.exc.ProgrammingError as prog_err:
        logging.getLogger(__name__).error(str(prog_err))


