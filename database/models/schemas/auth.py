import os
import re
import hashlib
import time

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, BigInteger, String, Index, DateTime, UniqueConstraint, ForeignKeyConstraint, \
    select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import BYTEA

from .base import Base
from database.conf import DEBUG
from database.models.exceptions.models_exc import UserNotFound, AddressNotFound, IncorrectInput


class Users(Base):

    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('tg_id', name='uq_tg_id'),
        {'schema': 'auth'} if not DEBUG else None,

    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(BigInteger, nullable=False)
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
            session: AsyncSession,
    ) -> Optional[int]:

        if not re.match(r'[А-Яа-яA-Za-z\s]{1,50}', first_name):
            raise IncorrectInput('Имя пользователя должно содержать от 1 до 50 символов.')

        if not re.match(r'[А-Яа-яA-Za-z\s]{1,50}', last_name):
            raise IncorrectInput('Имя пользователя должно содержать от 1 до 50 символов.')

        user = await session.execute(
            insert(cls).values(tg_id=tg_id, first_name=first_name, last_name=last_name).returning(cls.id)
        )

        user_id = user.scalar()

        return user_id

    @classmethod
    async def update_user(
            cls,
            tg_id: int,
            session: AsyncSession,
            first_name: str = None,
            last_name: str = None,
    ) -> Column[int]:

        user = await session.execute(select(cls).filter_by(tg_id=tg_id))

        user = user.scalar_one_or_none()

        if not user:
            raise UserNotFound(f'Пользователь с идентификатором {tg_id} не существует!')

        if not re.match(r'[А-Яа-яA-Za-z\s]{1,50}', first_name):
            raise IncorrectInput('Имя пользователя должно содержать от 1 до 50 символов.')

        if not re.match(r'[А-Яа-яA-Za-z\s]{1,50}', last_name):
            raise IncorrectInput('Имя пользователя должно содержать от 1 до 50 символов.')

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

        return user.id

    @classmethod
    async def get_user_id(
            cls,
            tg_id: int,
            session,
    ) -> int:

        user = await session.execute(select(cls.id).filter_by(tg_id=tg_id))

        user = user.scalar_one_or_none()

        if user is None:
            raise UserNotFound(f'Пользователь с идентификатором {tg_id} не существует!')

        return user


Index('idx_users_id', Users.id)


class Addresses(Base):

    __tablename__ = 'addresses'
    __table_args__ = (
        ForeignKeyConstraint(columns=['user_id'], refcolumns=['auth.users.id'], onupdate='CASCADE', ondelete='CASCADE'),
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

    @classmethod
    async def set_address(
            cls,
            user_id: int,
            country: str,
            city: str,
            street: str,
            apartment: str,
            phone: str,
            session: AsyncSession,
    ) -> int:
        print(type(phone), phone)
        if not re.match(r'[A-Z]{2}', country):
            raise IncorrectInput(f'Допускается длина поля country равной 2-м символам и может содержать только заглавные'
                                 f' латинские буквы.')

        if not re.match(r'[А-Яа-я\s]{5,50}', city):
            raise IncorrectInput(f'Допускается длина поля city от 5 до 50 символов.')

        if not re.match(r'[А-Яа-я\s]{5,255}', street):
            raise IncorrectInput(f'Допускается длина поля street от 5 до 255 символов.')

        if not re.match(r'[А-Яа-я\d]{1,10}', apartment):
            raise IncorrectInput(f'Допускается длина поля apartment от 1 до 10 символов.')

        if not re.match(r'^(\+7|8)\d{7,10}$', phone):
            raise IncorrectInput(f'Допустимый формат телефона +79999999999.')

        phone = ''.join(re.findall(r'\d', phone)).lstrip('+')

        address_id = await session.execute(
            insert(cls).values(
                user_id=user_id,
                country=country,
                city=city,
                street=street,
                apartment=apartment,
                phone=phone
            ).returning(cls.id)
        )

        address_id = address_id.scalar_one_or_none()

        if not address_id:
            raise AddressNotFound(f'Адрес для пользователя {user_id} не был добавлен.')

        return address_id


class Credentials(Base):

    __tablename__ = 'credentials'
    __table_args__ = (
        ForeignKeyConstraint(columns=['user_id'], refcolumns=['auth.users.id'], ondelete='CASCADE', onupdate='CASCADE'),
        {'schema': 'auth'} if not DEBUG else None,
    )

    user_id = Column(Integer, primary_key=True)
    salt = Column(BYTEA)
    password_hash = Column(String(length=255))
    auth_hash = Column(String(length=255))
    last_seen = Column(BigInteger)

    users = relationship('Users', back_populates='credentials', single_parent=True)

    async def set_password(
            self,
            password,
            salt_length: int = 16,
            iterations: int = 100000,
            hash_length: int = 64,
    ) -> None:

        if not re.match(r'[\w!@#$&\(\)\\-]{8,16}', password):
            raise IncorrectInput('Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские '
                                 'буквы в верхнем и нижнем регистре, цифры, а также специальные символы.')

        salt = os.urandom(salt_length)
        self.salt = salt

        salted_password = password.encode('utf-8') + salt

        key = hashlib.pbkdf2_hmac(
            'sha256',
            salted_password,
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

        if not re.match(r'[\w!@#$&\(\)\\-]{8,16}', password):
            raise IncorrectInput('Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские '
                                 'буквы в верхнем и нижнем регистре, цифры, а также специальные символы.')

        salted_password = password.encode('utf-8') + self.salt

        key = hashlib.pbkdf2_hmac(
            'sha256',
            salted_password,
            salt=self.salt,
            iterations=iterations,
            dklen=hash_length,
        )

        hash_hex = key.hex()

        return self.password_hash == hash_hex

    async def set_auth_hash(self):

        user_hash = hashlib.sha256().hexdigest()
        now = int(time.time())

        self.auth_hash = user_hash
        self.last_seen = now
