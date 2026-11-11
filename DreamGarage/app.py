"""
DreamGarage - the whole backend in ONE file
===========================================
HOW TO RUN (Windows):
    1. python -m pip install flask
    2. python app.py
    3. Open  http://127.0.0.1:5000

The database (dreamgarage.db) is created automatically the first time.
Admin account: configure DREAMGARAGE_ADMIN_EMAIL and DREAMGARAGE_ADMIN_PASSWORD

This file has 7 parts, top to bottom:
    1. Settings
    2. Database  (tables + sample cars + admin user)
    3. Helper functions
    4. Public pages        (home, cars, customize, order, info pages)
    5. Login / Register / Logout
    6. Customer dashboard + Admin panel
    7. API  (used by the pages' JavaScript: cars, reviews, place order)
"""
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, abort
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# 1. SETTINGS
# ---------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "local-development-only-change-me"

# The database file always sits next to app.py (no matter where you run from)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dreamgarage.db")

# Order goes: Pending -> Confirmed -> Production -> Shipped -> Delivered
STATUSES = ["Pending", "Confirmed", "Production", "Shipped", "Delivered"]
GST_RATE = 0.28

# Footer pages (about, faq ...). Their text is inside templates/info.html
INFO_PAGES = {
    "about": "About Us",
    "contact": "Contact Us",
    "faq": "FAQ",
    "privacy-policy": "Privacy Policy",
    "terms": "Terms of Service",
    "showrooms": "Showrooms",
}


# ---------------------------------------------------------
# 2. DATABASE
# ---------------------------------------------------------
TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    city TEXT,
    role TEXT DEFAULT 'customer',          -- 'customer' or 'admin'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,                -- Sedan / SUV / Sports / Electric
    bhp INTEGER,
    base_price REAL NOT NULL,
    spec TEXT,
    image TEXT,
    description TEXT
);
CREATE TABLE IF NOT EXISTS customization_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,                -- color / wheels / interior / accessories
    name TEXT NOT NULL,
    extra_price REAL NOT NULL DEFAULT 0,
    hex_code TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    car_id INTEGER NOT NULL,
    color TEXT,
    wheels TEXT,
    interior TEXT,
    accessories TEXT,
    total_price REAL NOT NULL,
    status TEXT DEFAULT 'Pending',
    payment TEXT DEFAULT 'UPI QR',
    delivery_name TEXT,
    delivery_phone TEXT,
    delivery_address TEXT,
    delivery_city TEXT,
    delivery_pin TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,               -- 1 to 5 stars
    comment TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (car_id) REFERENCES cars(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# (brand, name, category, bhp, base_price, spec, image in static/images/cars, description)
SAMPLE_CARS = [
    ("Ferrari", "F8 Tributo", "Sports", 710, 24000000, "3.9L Twin Turbo V8", "cars/ferrari.jpg", "Ferrari's mid-engine V8 supercar."),
    ("Rolls-Royce", "Phantom", "Sedan", 563, 69000000, "6.75L Twin Turbo V12", "cars/rolls-royce-phantom.jpg", "The pinnacle of automotive luxury."),
    ("Bugatti", "Chiron", "Sports", 1500, 250000000, "8.0L Quad Turbo W16", "cars/bugatti.jpg", "A hypercar that tops 400 km/h."),
    ("Lamborghini", "Urus Performante", "SUV", 666, 22000000, "4.0L Twin Turbo V8", "cars/lamborghini.jpg", "The world's fastest luxury SUV."),
    ("Porsche", "911 GT2 RS", "Sports", 690, 35000000, "3.8L Twin Turbo Flat-6", "cars/porsche.jpg", "The most powerful road-going 911."),
    ("BMW", "M4 Competition", "Sports", 503, 15000000, "3.0L Twin Turbo Inline-6", "cars/bmw.jpg", "A sharp, track-ready sports coupe."),
    ("Mercedes-AMG", "GT R", "Sports", 577, 30000000, "4.0L Twin Turbo V8", "cars/mercedes.jpg", "Hand-built AMG V8 sports car."),
    ("Mercedes-Maybach", "S 680", "Sedan", 604, 45000000, "6.0L Biturbo V12", "cars/maybach.jpg", "Ultimate expression of Mercedes luxury."),
    ("Porsche", "911 GT3 RS", "Sports", 518, 32000000, "4.0L Flat-6", "cars/porsche-911.jpg", "A road-legal race car for the track."),
]

# Model names used in older database files. If an old name is found, that car is updated
# to the matching row above (same position), so the name and the photo always agree.
OLD_CAR_NAMES = ["SF-X Coupe", "Ghost Phantom", "Continental GT", "Urus Performante", "Taycan Turbo S",
                 "Bentayga EWB", "EQS 680 4MATIC", "S 680", "DB12 Volante"]

# (category, name, extra price, colour code)
SAMPLE_OPTIONS = [
    ("color", "Pearl White", 0, "#f5f5f0"),
    ("color", "Matte Black", 150000, "#0a0a0a"),
    ("color", "Racing Red", 100000, "#b30000"),
    ("color", "Midnight Blue", 120000, "#0b1d3a"),
    ("wheels", 'Standard Alloy 18"', 0, None),
    ("wheels", 'Sport Alloy 20"', 200000, None),
    ("wheels", 'Carbon Fiber 21"', 350000, None),
    ("interior", "Leather Black", 0, None),
    ("interior", "Leather Tan", 80000, None),
    ("interior", "Alcantara Sport", 180000, None),
    ("accessories", "Panoramic Sunroof", 250000, None),
    ("accessories", "Premium Sound System", 320000, None),
    ("accessories", "Advanced Driver Assist", 400000, None),
    ("accessories", "Ambient Lighting Package", 90000, None),
]


def setup_database():
    """Create tables and fill sample data. Safe to run every time."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(TABLES)

    if conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO cars (brand, name, category, bhp, base_price, spec, image, description) "
            "VALUES (?,?,?,?,?,?,?,?)", SAMPLE_CARS)

    # older database files: bring the sample cars up to date (name, details and photo)
    for old_name, car in zip(OLD_CAR_NAMES, SAMPLE_CARS):
        conn.execute(
            "UPDATE cars SET brand=?, name=?, category=?, bhp=?, base_price=?, spec=?, image=?, description=? "
            "WHERE name = ?", car + (old_name,))

    if conn.execute("SELECT COUNT(*) FROM customization_options").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO customization_options (category, name, extra_price, hex_code) "
            "VALUES (?,?,?,?)", SAMPLE_OPTIONS)

    admin_email = os.environ.get("DREAMGARAGE_ADMIN_EMAIL")
    admin_password = os.environ.get("DREAMGARAGE_ADMIN_PASSWORD")
    if admin_email and admin_password and len(admin_password) >= 12:
        if conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] == 0:
            conn.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                         ("Admin", admin_email, generate_password_hash(admin_password), "admin"))

    conn.commit()
    conn.close()


setup_database()   # runs when the app starts


# ---------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------
def get_db():
    """Open the database. Rows can be used like dictionaries: row['name']."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def order_ref(order_id, created_at):
    """Order 12 placed in 2026  ->  'DG-2026-00012'."""
    year = (created_at or str(datetime.now().year))[:4]
    return f"DG-{year}-{order_id:05d}"


def inr(amount):
    """Indian number style: 24000000 -> '2,40,00,000'."""
    n = str(int(round(amount or 0)))
    if len(n) <= 3:
        return n
    last3, rest = n[-3:], n[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


app.jinja_env.filters["inr"] = inr      # lets pages write {{ price|inr }}


def login_required(page):
    """Put above a page function: only logged-in users can open it."""
    @wraps(page)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login?next=" + request.path)
        return page(*args, **kwargs)
    return wrapper


def admin_required(page):
    """Put above a page/API function: only the admin can open it."""
    @wraps(page)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify(success=False, message="Admin only. Please log in as admin."), 403
            return redirect("/login?next=" + request.path)
        return page(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_user():
    """Every page can use {{ current_user_name }} and {{ year }}."""
    return dict(current_user_name=session.get("user_name"), year=datetime.now().year)


def load_orders(where="", args=()):
    """Get orders together with car + customer info."""
    conn = get_db()
    rows = conn.execute(
        f"""SELECT o.*, c.brand, c.name AS car_name,
                   u.name AS user_name, u.email AS user_email
            FROM orders o
            JOIN cars c  ON c.id = o.car_id
            JOIN users u ON u.id = o.user_id
            {where}
            ORDER BY o.id DESC""", args).fetchall()
    conn.close()

    orders = []
    for r in rows:
        o = dict(r)
        o["ref"] = order_ref(r["id"], r["created_at"])          # DG-2026-00012
        o["date"] = (r["created_at"] or "")[:10]
        o["step"] = STATUSES.index(r["status"])                  # 0..4 for the tracker
        orders.append(o)
    return orders


# ---------------------------------------------------------
# 4. PUBLIC PAGES
# ---------------------------------------------------------
@app.route("/")
def home():
    conn = get_db()
    cars = conn.execute("SELECT * FROM cars ORDER BY id").fetchall()
    option_count = conn.execute("SELECT COUNT(*) FROM customization_options").fetchone()[0]
    conn.close()

    # featured = the first car of each type (Sports, Sedan, SUV ...), so the home page shows variety
    featured, seen = [], set()
    for c in cars:
        if c["category"] not in seen:
            seen.add(c["category"])
            featured.append(c)
    featured = featured[:3]
    stats = {
        "models": len(cars),
        "brands": len({c["brand"] for c in cars}),
        "options": option_count,
        "categories": len({c["category"] for c in cars}),
    }
    categories = sorted({c["category"] for c in cars})
    return render_template("index.html", featured=featured, stats=stats, categories=categories)


@app.route("/cars")
def cars_page():
    conn = get_db()
    cars = conn.execute(
        """SELECT c.*, ROUND(AVG(r.rating), 1) AS avg_rating, COUNT(r.id) AS review_count
           FROM cars c LEFT JOIN reviews r ON r.car_id = c.id
           GROUP BY c.id ORDER BY c.id""").fetchall()
    conn.close()
    brands = sorted({c["brand"] for c in cars})
    categories = sorted({c["category"] for c in cars})
    return render_template("cars.html", cars=cars, brands=brands, categories=categories)


@app.route("/customize")
def customize_page():
    return render_template("customize.html")


@app.route("/order")
def order_page():
    return render_template("order.html")


@app.route("/<page>")
def info_page(page):
    """/about /contact /faq /privacy-policy /terms /showrooms"""
    if page not in INFO_PAGES:
        abort(404)
    return render_template("info.html", page=page, title=INFO_PAGES[page])


@app.route("/track-order")
def track_order():
    return redirect("/dashboard#tracking")      # tracking now lives in the dashboard


# ---------------------------------------------------------
# 5. LOGIN / REGISTER / LOGOUT
# ---------------------------------------------------------
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_api():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(success=False, message="Email and password are required."), 400

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password"], password):
        return jsonify(success=False, message="Invalid email or password."), 401

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["role"] = user["role"]

    # After login go back to the page the user wanted (only our own pages)
    next_url = data.get("next") or ""
    if next_url.startswith("/") and not next_url.startswith("//"):
        redirect_to = next_url
    else:
        redirect_to = "/admin" if user["role"] == "admin" else "/dashboard"
    return jsonify(success=True, message="Login successful.", redirect=redirect_to)


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_api():
    data = request.get_json(silent=True) or {}
    first = (data.get("firstName") or "").strip()
    last = (data.get("lastName") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    city = (data.get("city") or "").strip()
    password = data.get("password") or ""

    if not first or not last or not email or not password:
        return jsonify(success=False, message="Please fill in all required fields."), 400
    if len(password) < 8:
        return jsonify(success=False, message="Password must be at least 8 characters."), 400

    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        conn.close()
        return jsonify(success=False, message="An account with this email already exists."), 409

    full_name = f"{first} {last}"
    cur = conn.execute(
        "INSERT INTO users (name, email, password, phone, city, role) VALUES (?,?,?,?,?, 'customer')",
        (full_name, email, generate_password_hash(password), phone, city))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    # Log the new user in straight away
    session["user_id"] = new_id
    session["user_name"] = full_name
    session["role"] = "customer"
    return jsonify(success=True, message="Account created successfully.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------------------------------------------------
# 6. CUSTOMER DASHBOARD + ADMIN PANEL
# ---------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard_page():
    if session.get("role") == "admin":
        return redirect("/admin")
    orders = load_orders("WHERE o.user_id = ?", (session["user_id"],))
    stats = {
        "total": len(orders),
        "in_transit": sum(1 for o in orders if o["status"] in ("Production", "Shipped")),
        "delivered": sum(1 for o in orders if o["status"] == "Delivered"),
        "pending": sum(1 for o in orders if o["status"] == "Pending"),
    }
    return render_template("dashboard.html", orders=orders, stats=stats)


@app.route("/admin")
@admin_required
def admin_page():
    orders = load_orders()
    conn = get_db()
    users = conn.execute(
        """SELECT u.*, COUNT(o.id) AS order_count
           FROM users u LEFT JOIN orders o ON o.user_id = u.id
           GROUP BY u.id ORDER BY u.id""").fetchall()
    conn.close()

    stats = {
        "orders": len(orders),
        "users": sum(1 for u in users if u["role"] == "customer"),
        "delivered": sum(1 for o in orders if o["status"] == "Delivered"),
        "pending": sum(1 for o in orders if o["status"] == "Pending"),
        # revenue = every order except those still waiting for confirmation
        "revenue": sum(o["total_price"] for o in orders if o["status"] != "Pending"),
    }

    # car pictures available in static/images (for the 'Add Car' form)
    car_folder = os.path.join(app.static_folder, "images", "cars")
    images = sorted("cars/" + f for f in os.listdir(car_folder)
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))

    return render_template("admin.html", orders=orders, users=users,
                           stats=stats, statuses=STATUSES, images=images)


@app.route("/api/admin/update_status", methods=["POST"])
@admin_required
def admin_update_status():
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").capitalize()

    if status not in STATUSES:
        return jsonify(success=False, message="Invalid status."), 400

    conn = get_db()
    cur = conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, data.get("order_id")))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify(success=False, message="Order not found."), 404
    return jsonify(success=True, message="Status updated.", status=status)


# ---------------------------------------------------------
# 7. API (called by JavaScript inside the pages)
# ---------------------------------------------------------
@app.route("/api/cars", methods=["GET"])
def api_cars_list():
    conn = get_db()
    cars = conn.execute("SELECT * FROM cars ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(c) for c in cars])


@app.route("/api/cars", methods=["POST"])
@admin_required
def api_cars_add():
    data = request.get_json(silent=True) or {}
    if not all(data.get(f) for f in ["brand", "name", "category", "base_price"]):
        return jsonify(success=False, message="Brand, name, category and base price are required."), 400

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO cars (brand, name, category, bhp, base_price, spec, image, description)
           VALUES (?,?,?,?,?,?,?,?)""",
        (data["brand"], data["name"], data["category"], data.get("bhp"),
         data["base_price"], data.get("spec", ""), data.get("image", ""),
         data.get("description", "")))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify(success=True, message="Car added successfully.", id=new_id)


@app.route("/api/cars/<int:car_id>", methods=["DELETE"])
@admin_required
def api_cars_delete(car_id):
    conn = get_db()
    if not conn.execute("SELECT id FROM cars WHERE id = ?", (car_id,)).fetchone():
        conn.close()
        return jsonify(success=False, message="Car not found."), 404

    # A car that already has orders cannot be deleted (it would break those orders)
    used = conn.execute("SELECT COUNT(*) FROM orders WHERE car_id = ?", (car_id,)).fetchone()[0]
    if used:
        conn.close()
        return jsonify(success=False, message=f"Cannot delete: {used} order(s) use this car."), 409

    conn.execute("DELETE FROM cars WHERE id = ?", (car_id,))
    conn.commit()
    conn.close()
    return jsonify(success=True, message="Car deleted successfully.")


@app.route("/api/cars/<int:car_id>/reviews", methods=["GET"])
def api_reviews_list(car_id):
    """Anyone can read reviews."""
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id, r.user_id, r.rating, r.comment, r.created_at, u.name
           FROM reviews r JOIN users u ON u.id = r.user_id
           WHERE r.car_id = ? ORDER BY r.id DESC""", (car_id,)).fetchall()
    conn.close()

    me, is_admin = session.get("user_id"), session.get("role") == "admin"
    reviews = [{
        "id": r["id"], "name": r["name"], "rating": r["rating"], "comment": r["comment"],
        "date": (r["created_at"] or "")[:10],
        "can_delete": is_admin or r["user_id"] == me,      # own review, or admin
    } for r in rows]
    average = round(sum(r["rating"] for r in rows) / len(rows), 1) if rows else 0
    return jsonify(reviews=reviews, average=average, count=len(rows),
                   logged_in=me is not None)


@app.route("/api/cars/<int:car_id>/reviews", methods=["POST"])
def api_reviews_add(car_id):
    """Logged-in users can review. One review per user per car (a new one replaces the old)."""
    if "user_id" not in session:
        return jsonify(success=False, message="Please log in to write a review."), 401

    data = request.get_json(silent=True) or {}
    comment = (data.get("comment") or "").strip()
    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        rating = 0

    if rating < 1 or rating > 5:
        return jsonify(success=False, message="Please choose 1 to 5 stars."), 400
    if len(comment) < 3:
        return jsonify(success=False, message="Please write a short comment."), 400
    if len(comment) > 500:
        return jsonify(success=False, message="Comment is too long (max 500 characters)."), 400

    conn = get_db()
    if not conn.execute("SELECT id FROM cars WHERE id = ?", (car_id,)).fetchone():
        conn.close()
        return jsonify(success=False, message="Car not found."), 404

    conn.execute("DELETE FROM reviews WHERE car_id = ? AND user_id = ?", (car_id, session["user_id"]))
    conn.execute("INSERT INTO reviews (car_id, user_id, rating, comment) VALUES (?,?,?,?)",
                 (car_id, session["user_id"], rating, comment))
    conn.commit()
    conn.close()
    return jsonify(success=True, message="Thank you! Your review is added.")


@app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def api_reviews_delete(review_id):
    """The writer of a review, or the admin, can delete it."""
    if "user_id" not in session:
        return jsonify(success=False, message="Please log in."), 401

    conn = get_db()
    review = conn.execute("SELECT user_id FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if not review:
        conn.close()
        return jsonify(success=False, message="Review not found."), 404
    if review["user_id"] != session["user_id"] and session.get("role") != "admin":
        conn.close()
        return jsonify(success=False, message="You can delete only your own review."), 403

    conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()
    return jsonify(success=True, message="Review deleted.")


@app.route("/api/customization-options")
def api_customization_options():
    conn = get_db()
    options = conn.execute("SELECT * FROM customization_options").fetchall()
    conn.close()
    return jsonify([dict(o) for o in options])


@app.route("/place_order", methods=["POST"])
def place_order():
    """Called from order.html after the customer pays."""
    if "user_id" not in session:
        return jsonify(success=False, message="Please log in to place an order."), 401

    data = request.get_json(silent=True) or {}
    cfg = data.get("config") or {}
    delivery = data.get("delivery") or {}

    conn = get_db()
    car = conn.execute("SELECT * FROM cars WHERE id = ?", (cfg.get("carId"),)).fetchone()
    if not car:
        conn.close()
        return jsonify(success=False, message="Car not found. Please choose a car again."), 400

    # The price is calculated HERE from the database,
    # so nobody can change the amount from the browser.
    def option_price(category, name):
        if not name:
            return 0
        row = conn.execute(
            "SELECT extra_price FROM customization_options WHERE category = ? AND name = ?",
            (category, name)).fetchone()
        return row["extra_price"] if row else 0

    color = (cfg.get("color") or {}).get("name")
    wheels = (cfg.get("wheels") or {}).get("name")
    interior = (cfg.get("interior") or {}).get("name")
    extra_names = [e.get("name") for e in cfg.get("extras", []) if e.get("name")]

    subtotal = (car["base_price"]
                + option_price("color", color)
                + option_price("wheels", wheels)
                + option_price("interior", interior)
                + sum(option_price("accessories", n) for n in extra_names))
    total = round(subtotal * (1 + GST_RATE))

    cur = conn.execute(
        """INSERT INTO orders (user_id, car_id, color, wheels, interior, accessories, total_price,
                               payment, delivery_name, delivery_phone, delivery_address,
                               delivery_city, delivery_pin, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session["user_id"], car["id"], color, wheels, interior,
         ", ".join(extra_names) or "None", total, "UPI QR",
         delivery.get("name"), delivery.get("phone"), delivery.get("address"),
         delivery.get("city"), delivery.get("pin"), delivery.get("notes")))
    conn.commit()
    order_id = cur.lastrowid
    created = conn.execute("SELECT created_at FROM orders WHERE id = ?", (order_id,)).fetchone()[0]
    conn.close()

    return jsonify(success=True, order_id=order_ref(order_id, created),
                   message="Order placed successfully.")


# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
