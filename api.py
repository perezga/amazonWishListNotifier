from fastapi import FastAPI
import json
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for the Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WISHLIST_FILE = "wishlist_data.json"

@app.get("/items")
def get_items():
    if not os.path.exists(WISHLIST_FILE):
        return []
    try:
        with open(WISHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
