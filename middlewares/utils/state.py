import logging
import time

import sqlalchemy.exc
from aiogram.types import Message

from database.models import Users, Credentials
from database.session import AsyncSessionLocal
from database.models.exceptions.models_exc import UserNotFound
from database.handlers.utils.redis_client import connect_redis_url
from middlewares.settings import AUTH_PERIOD
from signals.signals import Signal


async def check_auth_state(
        message: Message,
) -> Signal:

    tg_id = message.from_user.id

    r_cli = await connect_redis_url()

    auth_hash_presents_in_redis = await r_cli.exists(f'auth_hash:{tg_id}')

    if not auth_hash_presents_in_redis:

        try:
            async with AsyncSessionLocal() as session:
                async with session.begin() as transaction:

                    try:
                        user_id = await Users.get_user_id(tg_id, session)

                        credentials = Credentials(user_id=user_id)
                        await credentials.set_auth_hash()

                        await r_cli.hset(f'auth_hash:{user_id}', mapping={
                            'hash': credentials.auth_hash,
                            'last_seen': credentials.last_seen,
                        })
                        await transaction.commit()

                    except UserNotFound:
                        await transaction.rollback()
                        return Signal.NOT_REGISTERED
                    else:
                        return Signal.NOT_AUTHENTICATED

        except sqlalchemy.exc.SQLAlchemyError as sql_err:
            logging.getLogger(__name__).error(str(sql_err))
            return Signal.DATABASE_ERROR
    else:

        now = int(time.time())

        last_seen = await r_cli.hget(f'auth_hash:{tg_id}', 'last_seen')

        if not last_seen:
            return Signal.UNKNOWN_ERROR

        if now - last_seen > AUTH_PERIOD:

            return Signal.NOT_AUTHENTICATED
        else:
            return Signal.AUTHENTICATED








