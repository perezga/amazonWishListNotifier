from fastapi import FastAPI, HTTPException
import os
from fastapi.middleware.cors import CORSMiddleware
from models import SessionLocal, Item, PriceHistory
from sqlalchemy.orm import joinedload

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
        items = session.query(Item).all()
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
                "bestUsedPrice": item.best_used_price
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
