import os
import hashlib

from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, Index, DateTime, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship

from .base import Base
from database.conf import DEBUG
from database.models.exceptions.models_exc import UserNotFound


class Users(Base):

    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('tg_id', name='uq_tg_id'),
        {'schema': 'auth'} if not DEBUG else None,

    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(Integer, nullable=False)
    first_name = Column(String(length=50))
    last_name = Column(String(length=50))
    date_added = Column(DateTime, default=datetime.utcnow())
    date_changed = Column(DateTime, default=datetime.utcnow())

    addresses = relationship('Addresses', back_populates='users')
    credentials = relationship('Credentials', uselist=False, back_populates='users')
    orders = relationship('Orders', back_populates='users')

    @classmethod
    async def create_user(
            cls,
            tg_id: int,
            first_name: str,
            last_name: str,
            session,
    ) -> Column[int]:

        user = cls(tg_id=tg_id, first_name=first_name, last_name=last_name)

        session.add(user)

        await session.commit()

        return user.id

    @classmethod
    async def update_user(
            cls,
            tg_id: int,
            session,
            first_name: str = None,
            last_name: str = None,
    ) -> Column[int]:

        user = await session.query(cls).filter_by(tg_id=tg_id).scalar_one_or_none()

        if not user:
            raise UserNotFound(f'Пользователь с идентификатором {tg_id} не существует!')

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

        await session.commit()

        return user.id

    @classmethod
    async def get_user_id(
            cls,
            tg_id: int,
            session,
    ) -> Column[int]:

        user = await session.query(cls).filter_by(tg_id=tg_id).scalar_one_or_none()

        if not user:
            raise UserNotFound(f'Пользователь с идентификатором {tg_id} не существует!')

        return user.id


Index('idx_users_id', Users.id)


class Addresses(Base):

    __tablename__ = 'addresses'
    __table_args__ = (
        ForeignKeyConstraint(columns=['user_id'], refcolumns=['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
        {'schema': 'auth'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    country = Column(String(length=2), default='RU', nullable=False)
    city = Column(String(length=50), nullable=False)
    street = Column(String(255), nullable=False)
    apartment = Column(String(length=10), nullable=False)
    phone = Column(String(length=17), nullable=False)

    users = relationship('Users', back_populates='addresses')


class Credentials(Base):

    __tablename__ = 'credentials'
    __table_args__ = (
        ForeignKeyConstraint(columns=['user_id'], refcolumns=['users.id'], ondelete='CASCADE', onupdate='CASCADE'),
        {'schema': 'auth'} if not DEBUG else None,
    )

    user_id = Column(Integer, primary_key=True)
    salt = Column(String(length=255))
    password_hash = Column(String(length=255))
    auth_hash = Column(String(length=255))
    last_seen = Column(BigInteger)

    users = relationship('Users', back_populates='credentials', single_parent=True)

    async def set_password(
            self,
            password,
            salt_length: int = 16,
            iterations: int = 100000,
            hash_length: int = 64
    ) -> None:

        salt = os.urandom(salt_length)
        self.salt = salt

        salted_password = password + salt

        key = hashlib.pbkdf2_hmac(
            'sha256',
            salted_password.encode('utf-8'),
            iterations=iterations,
            salt=salt,
            dklen=hash_length,
        )

        hash_hex = key.hex()

        self.password_hash = hash_hex

    async def check_password(
            self,
            password: str,
            iterations: int = 100000,
            hash_length: int = 64
    ) -> bool:

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt=self.salt,
            iterations=iterations,
            dklen=hash_length,
        )

        hash_hex = key.hex()

        return self.password_hash == hash_hex
