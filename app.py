"""
=============================================================================
 Shreya Auto Enterprises — web application
 -----------------------------------------------------------------------------
 A small Python web server built with Flask. It does three jobs:

   1. Serves the website (the home page at  /  ).
   2. Receives inquiries from the contact form  ( POST /inquiry ),
      saves every one to data/inquiries.json, and emails them to the owner.
   3. Runs a password-protected admin panel at a SECRET address (config.ADMIN_PATH,
      not "/admin") where the owner adds or removes cars AND partners through web
      forms — photos are optimised to fast WebP automatically.

 The car listings live in  data/cars.json  and the partners in
 data/partners.json . The admin panel reads and writes those files, and the
 home page reads them to show the cards. There is no database to install — JSON
 files are enough for a showroom this size and are easy to back up (just copy
 the files).

 Run it with:   py app.py      (or double-click run.bat the first time)
=============================================================================
"""

import csv
import io
import json
import os
import re
import secrets
import smtplib
import threading
import time
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from functools import wraps
from urllib.parse import quote

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort, Response,
)
from werkzeug.utils import secure_filename

import config
import db

# Pillow is used to shrink + convert uploaded photos to WebP. If it is not
# installed the app still runs — it just stores the original photo as-is.
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# ── App setup ────────────────────────────────────────────────────────────────
# static_url_path="" means files in the  static/  folder are served from the
# site root, so the HTML can keep using paths like  assets/css/styles.css .
app = Flask(__name__, static_folder="static", static_url_path="")

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
CARS_FILE     = os.path.join(DATA_DIR, "cars.json")
INQUIRY_FILE  = os.path.join(DATA_DIR, "inquiries.json")
CARS_IMG_DIR  = os.path.join(BASE_DIR, "static", "assets", "img", "cars")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
TEAM_IMG_DIR  = os.path.join(BASE_DIR, "static", "assets", "img", "team")
ALLOWED_IMG   = {".jpg", ".jpeg", ".png", ".webp"}
# The live inventory files are the OWNER's data (edited through the admin on the live
# server), so they're gitignored and never overwritten by a code redeploy. These shipped
# "seed" copies are what a fresh checkout starts from — see the first-run seeding below.
CARS_SEED     = os.path.join(DATA_DIR, "cars.seed.json")
PARTNERS_SEED = os.path.join(DATA_DIR, "partners.seed.json")
REVIEWS_FILE  = os.path.join(DATA_DIR, "reviews.json")
REVIEWS_SEED  = os.path.join(DATA_DIR, "reviews.seed.json")


def _resolve_secret_key():
    """Keep logins stable & secret. Prefer SHREYA_SECRET_KEY / config.py; if those
    are still the shipped placeholder, generate a strong key once and remember it in
    the gitignored file .secret_key, so sessions survive restarts without a public key."""
    key = config.SECRET_KEY
    if key and not key.startswith("change-this"):
        return key
    key_file = os.path.join(BASE_DIR, ".secret_key")
    try:
        if os.path.exists(key_file):
            saved = open(key_file, encoding="utf-8").read().strip()
            if saved:
                return saved
        key = secrets.token_hex(32)
        with open(key_file, "w", encoding="utf-8") as fh:
            fh.write(key)
        return key
    except OSError:
        return secrets.token_hex(32)


app.secret_key = _resolve_secret_key()

# Production-friendly hardening — safe whether the app runs locally or on a host.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,           # JavaScript can't read the login cookie
    SESSION_COOKIE_SAMESITE="Lax",          # blocks the common cross-site request forgery
    SESSION_COOKIE_SECURE=not config.DEBUG, # production: only send the cookie over HTTPS
    MAX_CONTENT_LENGTH=40 * 1024 * 1024,    # allow multi-photo gallery uploads (per request)
)

# Make sure the data + photo-upload folders exist on EVERY startup — including when a
# production WSGI server imports the app (where the __main__ block below never runs).
for _folder in (DATA_DIR, CARS_IMG_DIR, TEAM_IMG_DIR):
    os.makedirs(_folder, exist_ok=True)

# First-run seeding: the live inventory files are gitignored (server-owned once the owner
# starts editing), so a fresh checkout won't have them. Copy the shipped seed into place
# ONLY when the live file is missing — this never touches an existing (live) file, so a
# redeploy can never wipe real inventory.
import shutil  # noqa: E402  (used only here, for the one-time seed copy)
for _live, _seed in ((CARS_FILE, CARS_SEED), (PARTNERS_FILE, PARTNERS_SEED), (REVIEWS_FILE, REVIEWS_SEED)):
    if not os.path.exists(_live) and os.path.exists(_seed):
        try:
            shutil.copyfile(_seed, _live)
            print(f"Seeded {os.path.basename(_live)} from {os.path.basename(_seed)} (first run).")
        except OSError as e:
            print(f"WARNING: could not seed {_live}: {e}")


@app.after_request
def set_security_headers(resp):
    """Defense-in-depth response headers. Database access goes through SQLAlchemy with
    bound parameters (so no SQL injection) and Jinja auto-escapes everything (so XSS is
    contained); these add the standard extras browsers look for. The CSP is permissive
    enough for the site's real sources (Google Fonts, the embedded map) — verify the live
    site's fonts + map after deploy."""
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline'; "
        "frame-src https://www.google.com https://www.youtube.com https://www.youtube-nocookie.com; "
        "media-src 'self'; connect-src 'self'; form-action 'self'; "
        "base-uri 'self'; frame-ancestors 'self'"
    )
    if not config.DEBUG:        # HSTS only makes sense once you're on HTTPS (production)
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


# ── Tiny JSON "database" helpers ─────────────────────────────────────────────
def read_json(path, default):
    """Read a JSON file, returning `default` if it doesn't exist yet — OR if it's
    unreadable/corrupt, so one bad file can never take the whole site down."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"WARNING: could not read {path}: {e} — using default.")
        return default


def write_json(path, data):
    """Save data atomically: write a temp file then replace, so a crash mid-write can
    never leave a half-written, corrupt file. Pretty-printed so it stays human-readable."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ── Database bootstrap ───────────────────────────────────────────────────────
# Everything (users, cars, partners, inquiries, reviews, buyers, sales, audit) now
# lives in a real database (SQLite by default, MySQL in production — see db.py /
# config.DATABASE_URL). On first run we create the tables, seed one superadmin, and
# import any existing JSON records so upgrading loses nothing. JSON files are kept
# as a backup; each table is only imported when it's still empty.
db.init_db()
db.ensure_superadmin(config.SUPERADMIN_USERNAME, config.SUPERADMIN_PASSWORD)
_present = db.count_rows()
if not _present["cars"]:
    _rows = read_json(CARS_FILE, [])
    if _rows:
        db.bulk_import_cars_from_json(_rows)
        print(f"Migrated {len(_rows)} cars from cars.json into the database.")
if not _present["partners"]:
    _rows = read_json(PARTNERS_FILE, [])
    if _rows:
        db.bulk_import_partners_from_json(_rows)
        print(f"Migrated {len(_rows)} partners from partners.json into the database.")
if not _present["inquiries"]:
    _rows = read_json(INQUIRY_FILE, [])
    if _rows:
        db.bulk_import_inquiries(_rows)
        print(f"Migrated {len(_rows)} inquiries from inquiries.json into the database.")
if not _present["reviews"]:
    _rows = read_json(REVIEWS_FILE, [])
    if _rows:
        db.bulk_import_reviews(_rows)
        print(f"Migrated {len(_rows)} reviews from reviews.json into the database.")


def load_cars():
    """All cars from the database (admin view — includes the private price)."""
    return db.all_cars_db()


def public_cars():
    """Cars for the PUBLIC site with the price removed — policy is 'Price on inquiry',
    so prices are never sent to visitors (not even hidden in the page source). The
    admin panel still uses load_cars() and shows the real prices to the owner."""
    out = []
    for c in load_cars():
        c = dict(c)
        c["price"] = ""
        out.append(c)
    return out


def save_cars(cars):
    write_json(CARS_FILE, cars)


def next_car_id(cars):
    """Pick the next free id (so every car has a unique number)."""
    return (max([c.get("id", 0) for c in cars]) + 1) if cars else 1


def load_partners():
    return db.all_partners_db()


def save_partners(partners):
    write_json(PARTNERS_FILE, partners)


def next_partner_id(partners):
    return (max([p.get("id", 0) for p in partners]) + 1) if partners else 1


def next_partner_order(partners):
    """The order to give a brand-new partner: one past the current highest."""
    return (max([p.get("order", 0) for p in partners]) + 1) if partners else 1


def public_reviews():
    """Only APPROVED reviews are shown on the site (newest first). Customer-submitted
    reviews stay hidden until the owner approves them in the admin — this stops spam
    or abuse from ever appearing publicly."""
    return db.approved_reviews()


# ── Email ────────────────────────────────────────────────────────────────────
def send_inquiry_email(data):
    """
    Email an inquiry to the owner. Does nothing (safely) if email isn't set up
    in config.py — the inquiry is still saved to the file either way.
    Returns True if an email was actually sent.
    """
    if not config.MAIL_USERNAME or not config.MAIL_PASSWORD:
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = f"New website inquiry — {data.get('name', 'Customer')}"
        msg["From"] = config.MAIL_USERNAME
        msg["To"] = config.MAIL_TO
        msg.set_content(
            "New inquiry from the Shreya Auto website:\n\n"
            f"Name:    {data.get('name','')}\n"
            f"Phone:   {data.get('phone','')}\n"
            f"Car:     {data.get('car','')}\n"
            f"Message: {data.get('message','')}\n"
            f"Time:    {data.get('time','')}\n"
        )
        with smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=20) as server:
            server.starttls()
            server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        # Never crash the website because email failed — just log it.
        print("Email failed:", e)
        return False


# ── Image processing ─────────────────────────────────────────────────────────
def process_upload(file_storage, base_name):
    """
    Take an uploaded photo and produce two fast WebP versions:
      <base>.webp       (full size, used by the photo lightbox)
      <base>-md.webp    (max 960px wide, used on the card — loads quickly)
    Returns (card_path, full_path) as website paths, or (None, None) on failure.
    """
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_IMG:
        return None, None
    os.makedirs(CARS_IMG_DIR, exist_ok=True)

    if not HAS_PILLOW:
        # No Pillow: just save the original file and use it for both.
        safe = secure_filename(base_name + ext)
        file_storage.save(os.path.join(CARS_IMG_DIR, safe))
        p = f"assets/img/cars/{safe}"
        return p, p

    try:
        img = Image.open(file_storage.stream).convert("RGB")

        # Full version (capped at IMAGE_MAX_WIDTH so it's never enormous)
        full = img.copy()
        if full.width > config.IMAGE_MAX_WIDTH:
            full = full.resize(
                (config.IMAGE_MAX_WIDTH,
                 round(full.height * config.IMAGE_MAX_WIDTH / full.width)),
                Image.LANCZOS,
            )
        full.save(os.path.join(CARS_IMG_DIR, base_name + ".webp"), "WEBP", quality=88, method=6)

        # Card version (max 960px wide)
        md = img.copy()
        if md.width > 960:
            md = md.resize((960, round(md.height * 960 / md.width)), Image.LANCZOS)
        md.save(os.path.join(CARS_IMG_DIR, base_name + "-md.webp"), "WEBP", quality=80, method=6)

        return f"assets/img/cars/{base_name}-md.webp", f"assets/img/cars/{base_name}.webp"
    except Exception as e:
        # A corrupt / non-image / decompression-bomb upload must not crash the admin.
        print("Car image processing failed:", e)
        return None, None


def process_partner_photo(file_storage, base_name):
    """Save an uploaded partner photo as one optimised WebP (max 800px wide)."""
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_IMG:
        return None
    os.makedirs(TEAM_IMG_DIR, exist_ok=True)
    if not HAS_PILLOW:
        safe = secure_filename(base_name + ext)
        file_storage.save(os.path.join(TEAM_IMG_DIR, safe))
        return f"assets/img/team/{safe}"
    try:
        img = Image.open(file_storage.stream).convert("RGB")
        if img.width > 800:
            img = img.resize((800, round(img.height * 800 / img.width)), Image.LANCZOS)
        img.save(os.path.join(TEAM_IMG_DIR, base_name + ".webp"), "WEBP", quality=82, method=6)
        return f"assets/img/team/{base_name}.webp"
    except Exception as e:
        print("Partner image processing failed:", e)
        return None


# ── Login protection for the admin pages (RBAC: per-user logins + roles) ─────
def current_user():
    """The logged-in user dict (id, username, role, …) or None."""
    return session.get("user")


def _role():
    u = session.get("user") or {}
    return u.get("role", "")


# Make current_user() / role available inside every template.
@app.context_processor
def _inject_user():
    return {"current_user": session.get("user"), "role": _role()}


def admin_required(view):
    """A guard: only a logged-in user with a fresh (non-idle) session gets through.
    Also forces a password change when the account is flagged for it."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user:
            return redirect(url_for("admin_login"))
        # Idle auto-logout: expire the session after N minutes of no activity.
        now = time.time()
        if now - session.get("last_seen", 0) > config.SESSION_TIMEOUT_MIN * 60:
            session.clear()
            flash("You were logged out after a period of inactivity. Please log in again.")
            return redirect(url_for("admin_login"))
        session["last_seen"] = now      # sliding window — every action refreshes it
        # A seeded / reset account must set a new password before doing anything else.
        if user.get("must_change_password") and request.endpoint not in (
                "admin_change_password", "admin_logout"):
            return redirect(url_for("admin_change_password"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    """Restrict a route to the given roles (use UNDER @admin_required)."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            if not user:
                return redirect(url_for("admin_login"))
            if user.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES  (each @app.route below is one web address the app responds to)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """The public home page. We pass the car + partner + approved-review lists in."""
    return render_template("index.html", cars=public_cars(), partners=load_partners(),
                           reviews=public_reviews())


@app.route("/cars")
def all_cars():
    """The full inventory page. Supports server-side filters: ?q=&fuel=&transmission="""
    q = request.args.get("q", "").strip().lower()
    fuel = request.args.get("fuel", "").strip().lower()
    trans = request.args.get("transmission", "").strip().lower()
    every = public_cars()
    fuels = sorted({c["fuel_type"] for c in every if c.get("fuel_type")})
    transmissions = sorted({c["transmission"] for c in every if c.get("transmission")})

    def keep(c):
        hay = f'{c.get("brand","")} {c.get("name","")} {c.get("year","")}'.lower()
        if q and q not in hay:
            return False
        if fuel and (c.get("fuel_type", "") or "").lower() != fuel:
            return False
        if trans and (c.get("transmission", "") or "").lower() != trans:
            return False
        return True

    cars = [c for c in every if keep(c)]
    return render_template("cars.html", cars=cars, partners=load_partners(),
                           q=request.args.get("q", ""), sel_fuel=request.args.get("fuel", ""),
                           sel_trans=request.args.get("transmission", ""),
                           fuels=fuels, transmissions=transmissions)


@app.route("/car/<int:car_id>")
def car_detail(car_id):
    """A car's own page. Only AVAILABLE cars are openable — a sold or unknown car
    sends the visitor back to the full inventory."""
    car = next((c for c in load_cars() if c.get("id") == car_id), None)
    if not car or car.get("status") == "sold":
        return redirect(url_for("all_cars"))
    car = dict(car); car["price"] = ""   # 'Price on inquiry' policy — never expose the price
    return render_template("car.html", car=car, partners=load_partners())


@app.route("/car/<int:car_id>/print")
def car_print(car_id):
    """A print-optimised window sticker / spec sheet for a walk-in customer."""
    car = next((c for c in load_cars() if c.get("id") == car_id), None)
    if not car:
        return redirect(url_for("all_cars"))
    car = dict(car); car["price"] = ""   # price stays private even on the printout
    return render_template("print_spec.html", car=car)


@app.route("/compare")
def compare():
    """Side-by-side comparison of up to 3 cars: /compare?id=1&id=2&id=3"""
    ids, seen = [], set()
    for raw in request.args.getlist("id"):
        try:
            i = int(raw)
        except ValueError:
            continue
        if i not in seen:
            seen.add(i); ids.append(i)
    ids = ids[:3]
    by_id = {c["id"]: c for c in public_cars()}
    cars = [by_id[i] for i in ids if i in by_id]
    return render_template("compare.html", cars=cars, all_cars=public_cars())


@app.route("/sitemap.xml")
def sitemap():
    """A dynamic XML sitemap so search engines can index every live car page."""
    base = request.url_root.rstrip("/")
    locs = [base + "/", base + "/cars"]
    for c in public_cars():
        if c.get("status") != "sold":
            locs.append(f"{base}/car/{c['id']}")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    parts += [f"  <url><loc>{u}</loc></url>" for u in locs]
    parts.append("</urlset>")
    return Response("\n".join(parts), mimetype="application/xml")


@app.route("/inquiry", methods=["POST"])
def inquiry():
    """
    The contact form posts here. We save the inquiry and try to email it.
    The website's JavaScript expects a small JSON reply ({"ok": true}).
    """
    # Clip every field — this is a PUBLIC endpoint, so cap how much can be stored.
    data = {
        "name":    request.form.get("name", "").strip()[:120],
        "phone":   request.form.get("phone", "").strip()[:40],
        "car":     request.form.get("car", "").strip()[:120],
        "message": request.form.get("message", "").strip()[:3000],
        "time":    datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if not data["name"] or not data["phone"]:
        return jsonify(ok=False, error="Name and phone are required."), 400

    db.add_inquiry(data["name"], data["phone"], data["car"], data["message"])

    # Send the email in the background so the customer gets an instant reply even if
    # Gmail is slow. The inquiry is already safely saved above, so nothing is lost.
    threading.Thread(target=send_inquiry_email, args=(data,), daemon=True).start()
    return jsonify(ok=True)


@app.route("/review", methods=["POST"])
def review():
    """
    A customer submits a review from the site. We save it as PENDING (approved=False)
    so nothing appears publicly until the owner approves it in the admin. Fields are
    clipped because this is a public endpoint. The JS expects a small JSON reply.
    """
    name = request.form.get("name", "").strip()[:80]
    text = request.form.get("text", "").strip()[:1000]
    location = request.form.get("location", "").strip()[:60]
    try:
        rating = int(request.form.get("rating", "5"))
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))
    if not name or not text:
        return jsonify(ok=False, error="Name and review are required."), 400

    db.add_review(name, rating, text, location)   # saved as PENDING (approved=False)
    return jsonify(ok=True)


# ---- Admin: login / logout --------------------------------------------------
# Simple in-memory brute-force throttle for the admin login (keyed by client IP).
_LOGIN_FAILS = {}      # ip -> [timestamps of recent failed attempts]
_LOGIN_MAX = 5         # this many failures...
_LOGIN_WINDOW = 900    # ...within this many seconds (15 min) pauses login for that IP


def _login_blocked(ip):
    now = time.time()
    fails = [t for t in _LOGIN_FAILS.get(ip, []) if now - t < _LOGIN_WINDOW]
    _LOGIN_FAILS[ip] = fails
    return len(fails) >= _LOGIN_MAX


@app.route(f"/{config.ADMIN_PATH}/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if _login_blocked(ip):
            flash("Too many attempts — please wait a few minutes and try again.")
            return render_template("admin.html", logged_in=False)
        username = request.form.get("username", "").strip()
        user = db.authenticate_user(username, request.form.get("password", ""))
        if user:
            _LOGIN_FAILS.pop(ip, None)
            session.clear()
            session["user"] = user
            session["last_seen"] = time.time()      # start the idle-timeout clock
            db.log_audit(user_id=user["id"], username=user["username"], action="login",
                         ip_address=ip)
            if user.get("must_change_password"):
                return redirect(url_for("admin_change_password"))
            return redirect(url_for("admin"))
        _LOGIN_FAILS.setdefault(ip, []).append(time.time())
        flash("Wrong username or password.")
    return render_template("admin.html", logged_in=False)


@app.route(f"/{config.ADMIN_PATH}/logout")
def admin_logout():
    user = session.get("user")
    if user:
        db.log_audit(user_id=user.get("id", 0), username=user.get("username", ""),
                     action="logout", ip_address=request.remote_addr or "?")
    session.clear()
    return redirect(url_for("admin_login"))


@app.route(f"/{config.ADMIN_PATH}/change-password", methods=["GET", "POST"])
@admin_required
def admin_change_password():
    """Forced/voluntary password change. Seeded or reset accounts land here first."""
    user = session["user"]
    if request.method == "POST":
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if len(new) < 6:
            flash("Password must be at least 6 characters.")
        elif new != confirm:
            flash("The two passwords don't match.")
        else:
            db.update_user(user["id"], password=new)
            user["must_change_password"] = False
            session["user"] = user
            db.log_audit(user_id=user["id"], username=user["username"],
                         action="change_password", ip_address=request.remote_addr or "?")
            flash("Password updated.")
            return redirect(url_for("admin"))
    return render_template("admin.html", logged_in=True, change_password=True)


def wa_number(phone):
    """Best-effort WhatsApp number from a customer-typed phone: digits only,
    prepend Nepal's 977 when it looks like a local 10-digit mobile."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10 and digits.startswith("9"):
        digits = "977" + digits
    return digits


def _lead_whatsapp(inq):
    """A pre-filled wa.me link so the team can reply to a lead in one click."""
    wa = wa_number(inq.get("phone", ""))
    if not wa:
        return ""
    car = inq.get("car", "")
    msg = f"Hello {inq.get('name', '')}, thank you for contacting Shreya Auto Enterprises"
    msg += f" about the {car}." if car else "."
    return "https://wa.me/" + wa + "?text=" + quote(msg)


def _price_to_int(price):
    """Pull the number out of a price string like 'Rs. 48,00,000' → 4800000 (0 if none)."""
    digits = "".join(ch for ch in (price or "") if ch.isdigit())
    return int(digits) if digits else 0


def _inr_group(n):
    """Group a number the Nepali/Indian way: 4800000 → '48,00,000'."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
    return head + "," + tail


def _norm_status(v):
    """Clamp a car status to one of the three allowed values."""
    return v if v in ("available", "sold", "reserved") else "available"


def _audit(action, target_type="", target_id=0, details=""):
    """Write an audit-log entry for the currently logged-in user."""
    u = session.get("user") or {}
    db.log_audit(user_id=u.get("id", 0), username=u.get("username", ""),
                 action=action, target_type=target_type, target_id=target_id,
                 details=details, ip_address=request.remote_addr or "?")


# ---- Admin: dashboard (inquiries + cars + partners) -------------------------
@app.route(f"/{config.ADMIN_PATH}")
@admin_required
def admin():
    role = _role()
    cars = load_cars()
    partners = load_partners()
    inquiries = db.all_inquiries()                       # newest first, each has a stable id
    for q in inquiries:
        q["wa"] = wa_number(q.get("phone", ""))
        q["car_wa"] = _lead_whatsapp(q)
    reviews = db.all_reviews()                           # pending first, then approved
    sales = db.all_sales()
    buyers = db.all_buyers()
    for b in buyers:
        b["total_fmt"] = ("Rs. " + _inr_group(b["total_spent"])) if b.get("total_spent") else "—"
    # Superadmin-only data
    users = db.all_users() if role == "superadmin" else []
    audit_logs = db.all_audit_logs() if role == "superadmin" else []
    db_status = db.check_db_status() if role == "superadmin" else {}

    total = db.sales_total()
    hot = sum(1 for q in inquiries if q.get("status") in ("new", "contacted", "test_drive"))
    stats = {
        "revenue":   ("Rs. " + _inr_group(total)) if total else "Rs. 0",
        "available": sum(1 for c in cars if c.get("status") == "available"),
        "sold":      sum(1 for c in cars if c.get("status") == "sold"),
        "reserved":  sum(1 for c in cars if c.get("status") == "reserved"),
        "leads_hot": hot,
        "buyers":    len(buyers),
        "cars":      len(cars),
    }
    sales_summary = {  # kept for the existing Car sales table header
        "count": len(sales),
        "total": ("Rs. " + _inr_group(total)) if total else "",
        "pending_reviews": sum(1 for r in reviews if not r.get("approved")),
    }
    return render_template(
        "admin.html", logged_in=True, cars=cars, partners=partners,
        inquiries=inquiries, reviews=reviews, sales=sales, buyers=buyers,
        users=users, audit_logs=audit_logs, db_status=db_status,
        stats=stats, sales_summary=sales_summary,
        mail_on=bool(config.MAIL_USERNAME and config.MAIL_PASSWORD), mail_to=config.MAIL_TO,
        lead_statuses=db.VALID_LEAD_STATUS)


@app.route(f"/{config.ADMIN_PATH}/test-email", methods=["POST"])
@admin_required
def admin_test_email():
    """Send a test email so the owner can confirm inquiry delivery works after
    setting the Gmail App Password — without submitting a fake inquiry."""
    if not (config.MAIL_USERNAME and config.MAIL_PASSWORD):
        flash("Email isn't set up yet — add SHREYA_MAIL_USERNAME + SHREYA_MAIL_PASSWORD "
              "(a Gmail App Password) in your .env or host settings. See DEPLOY.md §5b.")
        return redirect(url_for("admin"))
    ok = send_inquiry_email({
        "name": "Test — Shreya Auto admin panel",
        "phone": "—", "car": "—",
        "message": "This is a test email confirming that website inquiries will be delivered here.",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    if ok:
        flash(f"✅ Test email sent to {config.MAIL_TO}. Check the inbox (and the spam folder).")
    else:
        flash("❌ Test email failed. Double-check the Gmail address and the 16-character "
              "App Password (not your normal password). See DEPLOY.md §5b.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/inquiry/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_inquiry_delete():
    iid = int(request.form.get("id", 0))
    db.delete_inquiry(iid)
    _audit("delete_inquiry", "inquiry", iid)
    flash("Inquiry removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/review/approve", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_review_approve():
    rid = int(request.form.get("id", 0))
    db.approve_review(rid)
    _audit("approve_review", "review", rid)
    flash("Review approved — it's now live on the site.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/review/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_review_delete():
    rid = int(request.form.get("id", 0))
    db.delete_review(rid)
    _audit("delete_review", "review", rid)
    flash("Review removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/sale/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_sale_delete():
    sid = int(request.form.get("id", 0))
    db.delete_sale(sid)
    _audit("delete_sale", "sale", sid)
    flash("Sale record removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/sale/add", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_sale_add():
    """Directly record a sale for an available car from the Sales tab."""
    car_id = int(request.form.get("car_id", 0))
    car = db.get_car_db(car_id)
    if not car:
        flash("Please select a valid car.")
        return redirect(url_for("admin"))
    
    # Mark car as sold
    car["status"] = "sold"
    db.save_car_db(car)
    
    desc = " ".join(x for x in [car.get("brand"), car.get("name"), str(car.get("year", ""))] if x).strip()
    price = (request.form.get("sale_price", "").strip() or car.get("price", ""))[:60]
    
    buyer_id = int(request.form.get("buyer_id", 0))
    db.add_sale(
        car_id=car_id,
        car_desc=desc[:200],
        buyer_id=buyer_id,
        buyer_name=request.form.get("buyer_name", "").strip()[:120],
        buyer_phone=request.form.get("buyer_phone", "").strip()[:40],
        price=price,
        payment_method=request.form.get("payment_method", "").strip()[:50],
        notes=request.form.get("sale_notes", "").strip()[:1000],
        buyer_email=request.form.get("buyer_email", "").strip()[:120],
        buyer_address=request.form.get("buyer_address", "").strip()[:255],
        buyer_id_number=request.form.get("buyer_id_number", "").strip()[:60],
    )
    _audit("record_sale", "car", car_id, desc)
    flash(f"Sale recorded successfully for {desc}!")
    return redirect(url_for("admin"))



@app.route(f"/{config.ADMIN_PATH}/export/<kind>")
@admin_required
def admin_export(kind):
    """Download a table as a CSV spreadsheet (opens in Excel). A UTF-8 BOM is
    prepended so Excel shows Nepali text correctly."""
    tables = {
        "inquiries": (["time", "name", "phone", "car", "status", "message"], db.all_inquiries()),
        "reviews":   (["time", "name", "rating", "location", "approved", "text"], db.all_reviews()),
        "sales":     (["sold_on", "car_desc", "buyer_name", "buyer_phone", "price", "payment_method", "notes"], db.all_sales()),
        "buyers":    (["name", "phone", "email", "address", "id_number", "purchases", "total_spent"], db.all_buyers()),
        "cars":      (["id", "brand", "name", "year", "price", "status", "fuel_type", "transmission", "km"], db.all_cars_db()),
        "users":     (["username", "full_name", "email", "role", "is_active", "last_login"], db.all_users()),
    }
    if kind not in tables:
        abort(404)
    if kind == "users" and _role() != "superadmin":
        abort(403)
    cols, rows = tables[kind]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for r in rows:
        writer.writerow([r.get(c, "") for c in cols])
    fname = f"shreya-{kind}-{datetime.now().strftime('%Y-%m-%d')}.csv"
    return Response("﻿" + buf.getvalue(),
                    content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.route(f"/{config.ADMIN_PATH}/add", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_add():
    new_id = db.next_car_id_db()
    # Photo (optional). We name the files after the car id so they never clash.
    card_path = full_path = "assets/img/cars/car1-md.webp"   # a sensible default
    photo = request.files.get("photo")
    if photo and photo.filename:
        c, fpath = process_upload(photo, f"upload-{new_id}")
        if c:
            card_path, full_path = c, fpath
    specs = [s.strip() for s in request.form.get("specs", "").split(",") if s.strip()]
    car = db.save_car_db({
        "brand":  request.form.get("brand", "").strip(),
        "name":   request.form.get("name", "").strip(),
        "year":   request.form.get("year", "").strip(),
        "price":  request.form.get("price", "").strip(),
        "badge":  request.form.get("badge", "In stock").strip() or "In stock",
        "status": _norm_status(request.form.get("status")),
        "fuel_type":    request.form.get("fuel_type", "").strip(),
        "transmission": request.form.get("transmission", "").strip(),
        "specs":  specs,
        "desc":   request.form.get("desc", "").strip(),
        "video":  request.form.get("video", "").strip(),
        "img":    card_path, "full": full_path,
        "fit":    request.form.get("fit", "cover"),
        "accent": "#37b2ea",
        "seller_id":    int(request.form.get("seller_id", 0)),
        "seller_name":  request.form.get("seller_name", "").strip(),
        "seller_phone": request.form.get("seller_phone", "").strip(),
        "bought_price": request.form.get("bought_price", "").strip(),
    })
    _audit("add_car", "car", car["id"], f'{car["brand"]} {car["name"]}')
    flash("Car added.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/edit", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_edit():
    """Update an existing car (all fields; photo optional). Records a sale + buyer
    when the car is newly marked Sold."""
    car_id = int(request.form.get("id", 0))
    car = db.get_car_db(car_id)
    if not car:
        flash("Car not found.")
        return redirect(url_for("admin"))
    was_sold = (car.get("status") == "sold")
    new_status = _norm_status(request.form.get("status"))
    specs = [s.strip() for s in request.form.get("specs", "").split(",") if s.strip()]
    data = {
        "id":     car_id,
        "brand":  request.form.get("brand", "").strip() or car.get("brand", ""),
        "name":   request.form.get("name", "").strip() or car.get("name", ""),
        "year":   request.form.get("year", "").strip(),
        "price":  request.form.get("price", "").strip(),
        "badge":  request.form.get("badge", "").strip() or "In stock",
        "fit":    "contain" if request.form.get("fit") == "contain" else "cover",
        "status": new_status,
        "fuel_type":    request.form.get("fuel_type", "").strip(),
        "transmission": request.form.get("transmission", "").strip(),
        "specs":  specs,
        "desc":   request.form.get("desc", "").strip(),
        "video":  request.form.get("video", "").strip(),
        "seller_id":    int(request.form.get("seller_id", 0)),
        "seller_name":  request.form.get("seller_name", "").strip(),
        "seller_phone": request.form.get("seller_phone", "").strip(),
        "bought_price": request.form.get("bought_price", "").strip(),
    }
    photo = request.files.get("photo")
    if photo and photo.filename:
        card_path, full_path = process_upload(photo, f"upload-{car_id}")
        if card_path:
            data["img"], data["full"] = card_path, full_path
    db.save_car_db(data)
    # gallery: append any newly-uploaded photos, tagged by section
    for cat, field in (("exterior", "photos_exterior"), ("interior", "photos_interior")):
        for f in request.files.getlist(field):
            if f and f.filename:
                _card, _full = process_upload(f, f"upload-{car_id}-{secrets.token_hex(4)}")
                if _full:
                    db.add_car_gallery_photo(car_id, _full, cat)
    # Buyer capture on the available→sold transition (won't duplicate on re-save).
    if new_status == "sold" and not was_sold:
        desc = " ".join(x for x in [data["brand"], data["name"], str(data["year"])] if x).strip()
        buyer_id = int(request.form.get("buyer_id", 0))
        db.add_sale(
            car_id=car_id, car_desc=desc[:200], buyer_id=buyer_id,
            buyer_name=request.form.get("buyer_name", "").strip()[:120],
            buyer_phone=request.form.get("buyer_phone", "").strip()[:40],
            price=(request.form.get("sale_price", "").strip() or data["price"])[:60],
            payment_method=request.form.get("payment_method", "").strip()[:50],
            notes=request.form.get("sale_notes", "").strip()[:1000],
            buyer_email=request.form.get("buyer_email", "").strip()[:120],
            buyer_address=request.form.get("buyer_address", "").strip()[:255],
            buyer_id_number=request.form.get("buyer_id_number", "").strip()[:60],
        )
        _audit("record_sale", "car", car_id, desc)
    _audit("edit_car", "car", car_id, f'{data["brand"]} {data["name"]}')
    flash("Car updated.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/gallery/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_gallery_delete():
    """Remove a single photo from a car's gallery (leaves the file on disk)."""
    car_id = int(request.form.get("id", 0))
    db.delete_car_gallery_photo(car_id, request.form.get("src", ""))
    flash("Photo removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_delete():
    car_id = int(request.form.get("id", 0))
    db.delete_car_db(car_id)
    _audit("delete_car", "car", car_id)
    flash("Car removed.")
    return redirect(url_for("admin"))


# ---- Admin: partners --------------------------------------------------------
@app.route(f"/{config.ADMIN_PATH}/partner/add", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_partner_add():
    img = "assets/img/team/team-1.webp"   # sensible default if no photo is given
    photo = request.files.get("photo")
    if photo and photo.filename:
        p = process_partner_photo(photo, f"partner-{secrets.token_hex(4)}")
        if p:
            img = p
    try:
        order = int(request.form.get("order", "").strip())
    except ValueError:
        order = None
    partner = db.add_partner_db(request.form.get("name", "").strip(),
                                request.form.get("role", "Partner").strip() or "Partner",
                                img, order)
    _audit("add_partner", "partner", partner["id"], partner["name"])
    flash("Partner added.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/partner/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_partner_delete():
    pid = int(request.form.get("id", 0))
    db.delete_partner_db(pid)
    _audit("delete_partner", "partner", pid)
    flash("Partner removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/partner/update", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_partner_update():
    """Save the inline edits (name, role, order) for one partner card."""
    pid = int(request.form.get("id", 0))
    try:
        order = int(request.form.get("order", "").strip())
    except ValueError:
        order = None
    db.update_partner_db(pid, name=request.form.get("name", "").strip() or None,
                         role=request.form.get("role", "").strip() or None, order=order)
    _audit("edit_partner", "partner", pid)
    flash("Partner updated.")
    return redirect(url_for("admin"))


# ---- Admin: CRM lead status + buyers ----------------------------------------
@app.route(f"/{config.ADMIN_PATH}/inquiry/status", methods=["POST"])
@admin_required
def admin_inquiry_status():
    """Move a lead along the pipeline (new → contacted → test_drive → closed/lost)."""
    iid = int(request.form.get("id", 0))
    db.update_inquiry_status(iid, request.form.get("status", "new"))
    _audit("inquiry_status", "inquiry", iid, request.form.get("status", ""))
    flash("Lead status updated.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/buyer/add", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_buyer_add():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    if not (name or phone):
        flash("Please provide at least a name or phone number.")
        return redirect(url_for("admin"))
    b = db.get_or_create_buyer(
        name=name, phone=phone,
        email=request.form.get("email", "").strip(),
        address=request.form.get("address", "").strip(),
        id_number=request.form.get("id_number", "").strip(),
        notes=request.form.get("notes", "").strip()
    )
    _audit("create_buyer", "buyer", b.get("id", 0), b.get("name", ""))
    flash(f"Buyer '{b.get('name', 'New Buyer')}' registered successfully.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/buyer/delete", methods=["POST"])
@admin_required
@roles_required("superadmin", "manager")
def admin_buyer_delete():
    bid = int(request.form.get("id", 0))
    db.delete_buyer(bid)
    _audit("delete_buyer", "buyer", bid)
    flash("Buyer removed.")
    return redirect(url_for("admin"))


# ---- Admin: user accounts (superadmin only) ---------------------------------
@app.route(f"/{config.ADMIN_PATH}/user/create", methods=["POST"])
@admin_required
@roles_required("superadmin")
def admin_user_create():
    user, err = db.create_user(
        request.form.get("username", "").strip(),
        request.form.get("password", ""),
        role=request.form.get("role", "sales_rep"),
        full_name=request.form.get("full_name", "").strip(),
        email=request.form.get("email", "").strip(),
        must_change=True,
    )
    if err:
        flash(err)
    else:
        _audit("create_user", "user", user["id"], user["username"])
        flash(f"User '{user['username']}' created.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/user/update", methods=["POST"])
@admin_required
@roles_required("superadmin")
def admin_user_update():
    uid = int(request.form.get("id", 0))
    db.update_user(uid,
                   full_name=request.form.get("full_name", "").strip(),
                   email=request.form.get("email", "").strip(),
                   role=request.form.get("role", None),
                   password=request.form.get("password", "") or None)
    _audit("update_user", "user", uid)
    flash("User updated.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/user/toggle", methods=["POST"])
@admin_required
@roles_required("superadmin")
def admin_user_toggle():
    uid = int(request.form.get("id", 0))
    me = session.get("user") or {}
    if uid == me.get("id"):
        flash("You can't disable your own account.")
        return redirect(url_for("admin"))
    u = db.get_user(uid)
    if u:
        db.update_user(uid, is_active=not u["is_active"])
        _audit("toggle_user", "user", uid, "disabled" if u["is_active"] else "enabled")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/user/delete", methods=["POST"])
@admin_required
@roles_required("superadmin")
def admin_user_delete():
    uid = int(request.form.get("id", 0))
    me = session.get("user") or {}
    if uid == me.get("id"):
        flash("You can't delete your own account.")
        return redirect(url_for("admin"))
    db.delete_user(uid)
    _audit("delete_user", "user", uid)
    flash("User removed.")
    return redirect(url_for("admin"))


# ── Start the server ─────────────────────────────────────────────────────────
def open_browser():
    """Open the website in the default browser, once the server is up."""
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    # LOCAL launch only (py app.py / run.bat). In PRODUCTION you never run this file —
    # a real web host loads `application` from wsgi.py instead (see DEPLOY.md), which
    # turns debug off and switches on HTTPS-only cookies automatically.

    # Open the browser once on local startup (skipped on the reloader's child process).
    if config.DEBUG and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.2, open_browser).start()

    # host="0.0.0.0" lets your phone reach it on the same Wi-Fi.
    host = os.environ.get("SHREYA_HOST", "0.0.0.0")
    port = int(os.environ.get("SHREYA_PORT", "5000"))
    app.run(host=host, port=port, debug=config.DEBUG)
