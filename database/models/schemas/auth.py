from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Index, DateTime, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship

from .base import Base
from database.conf import DEBUG


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
    credentials = relationship('Credentials', back_populates='users')
    orders = relationship('Orders', back_populates='users')


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
    password_hash = Column(String(length=255))
    auth_hash = Column(String(length=255))
    last_seen = Column(BigInteger)

    users = relationship('Users', back_populates='credentials', single_parent=True)