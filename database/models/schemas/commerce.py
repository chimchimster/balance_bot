import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DECIMAL, Boolean, ForeignKey, Index, DateTime, Enum
from sqlalchemy.orm import relationship

from .base import Base
from database.conf import DEBUG


class ItemsImages(Base):

    __tablename__ = 'items_images'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    item_id = Column(Integer, ForeignKey('commerce.items.id'), primary_key=True)
    image_id = Column(Integer, ForeignKey('commerce.images.id'), primary_key=True)


class Items(Base):

    __tablename__ = 'items'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL, nullable=False)
    available = Column(Boolean, default=True)
    brand_id = Column(Integer, ForeignKey('commerce.brands.id'))

    images = relationship('Images', secondary='commerce.items_images', back_populates='items')
    item_meta = relationship('ItemMeta', back_populates='items')
    brands = relationship('Brands', back_populates='items')


Index('idx_items_id', Items.id)


class Images(Base):

    __tablename__ = 'images'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(255), nullable=False)

    items = relationship('Items', secondary='commerce.items_images', back_populates='images')


Index('idx_images_id', Images.id)


class ItemMeta(Base):

    __tablename__ = 'item_meta'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    class Sex(enum.Enum):
        male = 'male'
        female = 'female'

    item_id = Column(Integer, ForeignKey('commerce.items.id'), primary_key=True)
    size = Column(DECIMAL(3, 2), nullable=False)
    color = Column(String(15), nullable=False)
    sex = Column(Enum(Sex, schema='commerce'))

    items = relationship('Items', back_populates='item_meta', uselist=False, single_parent=True)


class Brands(Base):

    __tablename__ = 'brands'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=50))

    items = relationship('Items', back_populates='brands', uselist=False)


Index('idx_brand_id', Brands.id)


class Colors(Base):

    __tablename__ = 'colors'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=15))


class Sizes(Base):

    __tablename__ = 'sizes'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    size = Column(DECIMAL(4, 2))


class OrderItem(Base):

    __tablename__ = 'order_item'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    order_id = Column(Integer, ForeignKey('commerce.orders.id'), primary_key=True)
    item_id = Column(Integer, ForeignKey('commerce.items.id'), primary_key=True)


class Orders(Base):

    __tablename__ = 'orders'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('auth.users.id' if not DEBUG else 'users.id'))
    date_created = Column(DateTime, default=datetime.utcnow())

    users = relationship('Users', back_populates='orders')
    deliveries = relationship('Deliveries', back_populates='orders')


class Deliveries(Base):

    __tablename__ = 'deliveries'
    __table_args__ = (
        {'schema': 'commerce'} if not DEBUG else None,
    )

    class Statuses(enum.Enum):
        in_stock = 'in_stock'
        on_the_way = 'on_the_way'
        delivered = 'delivered'

    order_id = Column(Integer, ForeignKey('commerce.orders.id'), primary_key=True)
    status = Column(Enum(Statuses, schema='commerce'), default=Statuses.in_stock)
    track_code = Column(String(length=100))

    orders = relationship('Orders', back_populates='deliveries', single_parent=True)
