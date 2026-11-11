# DreamGarage — Luxury Car Customization and Online Ordering System

A Python Flask web application concept for browsing luxury cars, customizing a vehicle, managing a cart/order, and viewing customer and admin dashboards.

## Features
- User registration and login
- Luxury car catalogue and details
- Vehicle customization
- Cart and order placement
- Customer dashboard and order tracking
- Admin dashboard and order management
- Demo payment screen (no real payment processing)

## Tech stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- Database: SQLite

## Run locally (Windows)
1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set a development secret key in your terminal (PowerShell):
   ```powershell
   $env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Visit http://127.0.0.1:5000

## Optional admin setup
To create the initial admin account on first database setup, set `DREAMGARAGE_ADMIN_EMAIL` and `DREAMGARAGE_ADMIN_PASSWORD` before running the app. Use a unique password of at least 12 characters. The app does not include a public default admin password. If an existing local database already has an admin, its credentials are not changed.

## Important notes
- The payment page is a UI demonstration only. It does not verify or process UPI payments.
- Do not commit personal QR codes, real customer data, database files, passwords, API keys, or secret keys.
- Car photographs and other third-party assets should only be published if you have permission to share them.

## Project status
Academic portfolio project / demonstration application.
