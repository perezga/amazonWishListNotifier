from sqlalchemy import Column, String, Float, DateTime, ForeignKey, create_engine, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String)

class Wishlist(Base):
    __tablename__ = "wishlists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    url = Column(String)
    
    items = relationship("Item", back_populates="wishlist")

class Item(Base):
    __tablename__ = "items"
    id = Column(String, primary_key=True)
    title = Column(String)
    url = Column(String)
    image_url = Column(String)
    best_used_price = Column(Float)
    wishlist_id = Column(Integer, ForeignKey("wishlists.id"))
    
    wishlist = relationship("Wishlist", back_populates="items")
    history = relationship("PriceHistory", back_populates="item", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, ForeignKey("items.id"))
    price = Column(Float)
    price_used = Column(Float)
    savings = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    item = relationship("Item", back_populates="history")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, ForeignKey("items.id"))
    title = Column(String)
    message = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Integer, default=0) # 0 for unread, 1 for read

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/wishlist")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Migration and initialization is now handled by Alembic
