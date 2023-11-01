from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DECIMAL, Boolean, ForeignKey, Index, DateTime, Enum
from sqlalchemy.orm import relationship

from database.models.base import Base


class ItemsImages(Base):

    __tablename__ = 'items_images'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    item_id = Column(Integer, ForeignKey('images.id'), primary_key=True)
    image_id = Column(Integer, ForeignKey('images.id'), primary_key=True)


class Items(Base):

    __tablename__ = 'items'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(DECIMAL, nullable=False)
    available = Column(Boolean, default=True)
    brand_id = Column(Integer, ForeignKey('brand.id'))

    images = relationship(secondary=ItemsImages, back_populates='items')
    items_meta = relationship('ItemMeta', back_populates='items')
    brands = relationship('Brand', back_populates='items')


Index('idx_items_id', Items.c.id)


class Images(Base):

    __tablename__ = 'images'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(255), nullable=False)

    items = relationship(secondary=ItemsImages, back_populates='images')


Index('idx_images_id', Images.c.id)


class ItemMeta(Base):

    __tablename__ = 'item_meta'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    item_id = Column(Integer, primary_key=True)

    items = relationship('Items', back_populates='item_meta', single_parent=True)


class Brands(Base):

    __tablename__ = 'brands'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(length=50))

    items = relationship('Items', back_populates='brands', uselist=False)


Index('idx_brand_id', Brands.c.id)


class OrderItem(Base):

    __tablename__ = 'order_item'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    order_id = Column(Integer, ForeignKey('orders.id'))
    item_id = Column(Integer, ForeignKey('items.id'))


class Orders(Base):

    __tablename__ = 'orders'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('auth.users.id'))
    date_created = Column(DateTime, default=datetime.utcnow())

    users = relationship('Users', back_populates='orders')
    deliveries = relationship('Deliveries', back_populates='orders')


class Deliveries(Base):

    __tablename__ = 'deliveries'
    __table_args__ = (
        {'schema': 'commerce'},
    )

    order_id = Column(Integer, ForeignKey('orders.id'))
    status = Column(Enum)

    orders = relationship('Orders', back_populates='deliveries', single_parent=True)
