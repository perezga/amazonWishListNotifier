from sqlalchemy import Column, String, Float, DateTime, ForeignKey, create_engine, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(String, primary_key=True)
    title = Column(String)
    url = Column(String)
    image_url = Column(String)
    best_used_price = Column(Float)
    
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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/wishlist")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
