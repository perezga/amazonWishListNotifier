# Amazon Wishlist Android App

This is a Jetpack Compose Android app that displays items and prices from your Amazon wishlist.

## How it works
1. The Python scraper (`amazonPriceUpdateNotification.py`) periodically saves your wishlist items to `wishlist_data.json`.
2. The FastAPI server (`api.py`) serves this JSON data via a REST API.
3. This Android app fetches the data from the API and displays it in a clean UI.

## Setup Instructions

### 1. Run the Backend
Ensure you have the Python dependencies installed:
```bash
pip install -r requirements.txt
```

Run the scraper (in one terminal):
```bash
python amazonPriceUpdateNotification.py
```

Run the API server (in another terminal):
```bash
python api.py
```

### 2. Configure the Android App
Open `android_app/app/src/main/java/com/example/amazonwishlist/data/WishlistApi.kt` and update the `BASE_URL` with your computer's local IP address (e.g., `http://192.168.1.100:8000/`).

### 3. Build and Run
- Open the `android_app` directory in Android Studio.
- Sync Gradle.
- Run the app on an emulator or physical device.

## Features
- **Real-time Price Tracking**: Shows current price and best used price.
- **Savings Indicator**: Highlights items with significant price drops.
- **Visuals**: Displays item images using Coil.
- **Material 3 Design**: Clean and modern UI.
