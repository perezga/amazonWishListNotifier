from fastapi import FastAPI, HTTPException
import os
from fastapi.middleware.cors import CORSMiddleware
from models import SessionLocal, Item, PriceHistory, Notification, Wishlist
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

class WishlistCreate(BaseModel):
    url: String = "" # Simplified for Pydantic

@app.get("/wishlists")
def get_wishlists():
    session = SessionLocal()
    try:
        return session.query(Wishlist).all()
    finally:
        session.close()

@app.post("/wishlists")
def add_wishlist(wishlist_data: dict):
    url = wishlist_data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    session = SessionLocal()
    try:
        existing = session.query(Wishlist).filter(Wishlist.url == url).first()
        if existing:
            return existing
        
        # We don't know the name yet, scraper will update it. 
        # Use a placeholder or extract from URL
        name = url.split("/")[-1]
        new_wishlist = Wishlist(url=url, name=name)
        session.add(new_wishlist)
        session.commit()
        session.refresh(new_wishlist)
        return new_wishlist
    finally:
        session.close()

@app.delete("/wishlists/{wishlist_id}")
def delete_wishlist(wishlist_id: int):
    session = SessionLocal()
    try:
        wishlist = session.query(Wishlist).filter(Wishlist.id == wishlist_id).first()
        if not wishlist:
            raise HTTPException(status_code=404, detail="Wishlist not found")
        
        # Items and PriceHistory will stay, or we can delete them. 
        # Let's delete items associated with this wishlist.
        session.query(Item).filter(Item.wishlist_id == wishlist_id).delete()
        session.delete(wishlist)
        session.commit()
        return {"status": "success"}
    finally:
        session.close()

app = FastAPI()

# Enable CORS for the Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/items")
def get_items():
    session = SessionLocal()
    try:
        items = session.query(Item).options(joinedload(Item.wishlist)).all()
        result = []
        for item in items:
            latest_price = session.query(PriceHistory)\
                .filter(PriceHistory.item_id == item.id)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
            
            result.append({
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "imageURL": item.image_url,
                "price": latest_price.price if latest_price else None,
                "priceUsed": latest_price.price_used if latest_price else None,
                "savings": latest_price.savings if latest_price else 0,
                "bestUsedPrice": item.best_used_price,
                "wishlistName": item.wishlist.name if item.wishlist else "Unknown",
                "wishlistUrl": item.wishlist.url if item.wishlist else ""
            })
        return result
    finally:
        session.close()

@app.get("/items/{item_id}/history")
def get_item_history(item_id: str):
    session = SessionLocal()
    try:
        history = session.query(PriceHistory)\
            .filter(PriceHistory.item_id == item_id)\
            .order_by(PriceHistory.timestamp.asc())\
            .all()
        return history
    finally:
        session.close()

@app.get("/notifications")
def get_notifications():
    session = SessionLocal()
    try:
        notifications = session.query(Notification).order_by(Notification.timestamp.desc()).limit(50).all()
        return notifications
    finally:
        session.close()

@app.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int):
    session = SessionLocal()
    try:
        notification = session.query(Notification).filter(Notification.id == notification_id).first()
        if notification:
            notification.is_read = 1
            session.commit()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Notification not found")
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
