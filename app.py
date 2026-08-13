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

import json
import os
import secrets
import smtplib
import threading
import time
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort,
)
from werkzeug.utils import secure_filename

import config

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
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,    # reject uploads bigger than 12 MB
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
    """Defense-in-depth response headers. The site has no database (so no SQL injection)
    and Jinja auto-escapes everything (so XSS is contained); these add the standard extras
    browsers look for. The CSP is permissive enough for the site's real sources (Google
    Fonts, the embedded map) — verify the live site's fonts + map after deploy."""
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


def load_cars():
    return read_json(CARS_FILE, [])


def save_cars(cars):
    write_json(CARS_FILE, cars)


def next_car_id(cars):
    """Pick the next free id (so every car has a unique number)."""
    return (max([c.get("id", 0) for c in cars]) + 1) if cars else 1


def load_partners():
    return read_json(PARTNERS_FILE, [])


def save_partners(partners):
    write_json(PARTNERS_FILE, partners)


def next_partner_id(partners):
    return (max([p.get("id", 0) for p in partners]) + 1) if partners else 1


def next_partner_order(partners):
    """The order to give a brand-new partner: one past the current highest."""
    return (max([p.get("order", 0) for p in partners]) + 1) if partners else 1


def load_reviews():
    return read_json(REVIEWS_FILE, [])


def save_reviews(reviews):
    write_json(REVIEWS_FILE, reviews)


def next_review_id(reviews):
    return (max([r.get("id", 0) for r in reviews]) + 1) if reviews else 1


def public_reviews():
    """Only APPROVED reviews are shown on the site (newest first). Customer-submitted
    reviews stay hidden until the owner approves them in the admin — this stops spam
    or abuse from ever appearing publicly."""
    revs = [r for r in load_reviews() if r.get("approved")]
    revs.sort(key=lambda r: r.get("id", 0), reverse=True)
    return revs


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


# ── Login protection for the admin pages ─────────────────────────────────────
# Fail-safe: never let a LIVE site run with the shipped default password. wsgi.py
# refuses to even start in that case; this in-app flag is the backstop for anyone
# who runs app.py directly with debug turned off.
ADMIN_LOCKED = (not config.DEBUG) and config.PASSWORD_IS_DEFAULT


def admin_required(view):
    """A guard: only a logged-in admin with a fresh (non-idle) session gets through."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if ADMIN_LOCKED:
            # Misconfigured production (still the default password) — deny everything.
            abort(503)
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        # Idle auto-logout: expire the session after N minutes of no admin activity.
        now = time.time()
        if now - session.get("last_seen", 0) > config.SESSION_TIMEOUT_MIN * 60:
            session.pop("is_admin", None)
            session.pop("last_seen", None)
            flash("You were logged out after a period of inactivity. Please log in again.")
            return redirect(url_for("admin_login"))
        session["last_seen"] = now      # sliding window — every action refreshes it
        return view(*args, **kwargs)
    return wrapped


# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES  (each @app.route below is one web address the app responds to)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """The public home page. We pass the car + partner + approved-review lists in."""
    return render_template("index.html", cars=load_cars(), partners=load_partners(),
                           reviews=public_reviews())


@app.route("/cars")
def all_cars():
    """The full inventory page — every car in a grid with brand filters."""
    return render_template("cars.html", cars=load_cars(), partners=load_partners())


@app.route("/car/<int:car_id>")
def car_detail(car_id):
    """A car's own page. Only AVAILABLE cars are openable — a sold or unknown car
    sends the visitor back to the full inventory."""
    car = next((c for c in load_cars() if c.get("id") == car_id), None)
    if not car or car.get("status") == "sold":
        return redirect(url_for("all_cars"))
    return render_template("car.html", car=car, partners=load_partners())


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

    inquiries = read_json(INQUIRY_FILE, [])
    inquiries.append(data)
    write_json(INQUIRY_FILE, inquiries)

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

    reviews = load_reviews()
    reviews.append({
        "id":       next_review_id(reviews),
        "name":     name,
        "rating":   rating,
        "text":     text,
        "location": location,
        "time":     datetime.now().strftime("%Y-%m-%d"),
        "approved": False,     # held for admin approval before it shows on the site
    })
    save_reviews(reviews)
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
    if ADMIN_LOCKED:
        # Live site still on the default password — refuse to log anyone in.
        flash("Admin is disabled until a real password is set (SHREYA_ADMIN_PASSWORD). See DEPLOYER.md.")
        return render_template("admin.html", logged_in=False), 503
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if _login_blocked(ip):
            flash("Too many attempts — please wait a few minutes and try again.")
            return render_template("admin.html", logged_in=False)
        # Constant-time compare so the password can't be guessed by timing the response.
        if secrets.compare_digest(request.form.get("password", ""), config.ADMIN_PASSWORD):
            _LOGIN_FAILS.pop(ip, None)
            session["is_admin"] = True
            session["last_seen"] = time.time()      # start the idle-timeout clock
            return redirect(url_for("admin"))
        _LOGIN_FAILS.setdefault(ip, []).append(time.time())
        flash("Wrong password.")
    return render_template("admin.html", logged_in=False)


@app.route(f"/{config.ADMIN_PATH}/logout")
def admin_logout():
    session.pop("is_admin", None)
    session.pop("last_seen", None)
    return redirect(url_for("admin_login"))


def wa_number(phone):
    """Best-effort WhatsApp number from a customer-typed phone: digits only,
    prepend Nepal's 977 when it looks like a local 10-digit mobile."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10 and digits.startswith("9"):
        digits = "977" + digits
    return digits


# ---- Admin: dashboard (inquiries + cars + partners) -------------------------
@app.route(f"/{config.ADMIN_PATH}")
@admin_required
def admin():
    items = read_json(INQUIRY_FILE, [])
    for q in items:
        q["wa"] = wa_number(q.get("phone", ""))
    inquiries = list(reversed(list(enumerate(items))))   # newest first, keep original index for delete
    mail_on = bool(config.MAIL_USERNAME and config.MAIL_PASSWORD)
    # Reviews: pending (awaiting approval) first, then approved — newest within each group.
    reviews = sorted(load_reviews(), key=lambda r: (r.get("approved", False), -r.get("id", 0)))
    return render_template("admin.html", logged_in=True, cars=load_cars(),
                           partners=load_partners(), inquiries=inquiries, mail_on=mail_on,
                           mail_to=config.MAIL_TO, reviews=reviews)


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
def admin_inquiry_delete():
    idx = int(request.form.get("index", -1))
    items = read_json(INQUIRY_FILE, [])
    if 0 <= idx < len(items):
        items.pop(idx)
        write_json(INQUIRY_FILE, items)
        flash("Inquiry removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/review/approve", methods=["POST"])
@admin_required
def admin_review_approve():
    rid = int(request.form.get("id", 0))
    reviews = load_reviews()
    for r in reviews:
        if r.get("id") == rid:
            r["approved"] = True
            break
    save_reviews(reviews)
    flash("Review approved — it's now live on the site.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/review/delete", methods=["POST"])
@admin_required
def admin_review_delete():
    rid = int(request.form.get("id", 0))
    save_reviews([r for r in load_reviews() if r.get("id") != rid])
    flash("Review removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/add", methods=["POST"])
@admin_required
def admin_add():
    cars = load_cars()
    new_id = next_car_id(cars)

    # Photo (optional). We name the files after the car id so they never clash.
    card_path = full_path = "assets/img/cars/car1-md.webp"   # a sensible default
    photo = request.files.get("photo")
    if photo and photo.filename:
        c, fpath = process_upload(photo, f"upload-{new_id}")
        if c:
            card_path, full_path = c, fpath

    # "53,000 km, Petrol, 1500 cc" → ["53,000 km", "Petrol", "1500 cc"]
    specs = [s.strip() for s in request.form.get("specs", "").split(",") if s.strip()]

    cars.append({
        "id":     new_id,
        "brand":  request.form.get("brand", "").strip(),
        "name":   request.form.get("name", "").strip(),
        "year":   request.form.get("year", "").strip(),
        "img":    card_path,
        "full":   full_path,
        "fit":    request.form.get("fit", "cover"),
        "price":  request.form.get("price", "").strip(),
        "badge":  request.form.get("badge", "In stock").strip() or "In stock",
        "specs":  specs,
        "status": "sold" if request.form.get("status") == "sold" else "available",
        "desc":   request.form.get("desc", "").strip(),
    })
    save_cars(cars)
    flash("Car added.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/edit", methods=["POST"])
@admin_required
def admin_edit():
    """Update an existing car in place (all fields; photo optional). Keeps the same
    id and, if no new photo is uploaded, keeps the current photo."""
    car_id = int(request.form.get("id", 0))
    cars = load_cars()
    for c in cars:
        if c.get("id") == car_id:
            c["brand"] = request.form.get("brand", "").strip() or c.get("brand", "")
            c["name"]  = request.form.get("name", "").strip() or c.get("name", "")
            c["year"]  = request.form.get("year", "").strip()
            c["price"] = request.form.get("price", "").strip()
            c["badge"] = request.form.get("badge", "").strip() or "In stock"
            c["fit"]   = "contain" if request.form.get("fit") == "contain" else "cover"
            c["specs"] = [s.strip() for s in request.form.get("specs", "").split(",") if s.strip()]
            c["status"] = "sold" if request.form.get("status") == "sold" else "available"
            c["desc"]  = request.form.get("desc", "").strip()
            photo = request.files.get("photo")
            if photo and photo.filename:
                card_path, full_path = process_upload(photo, f"upload-{car_id}")
                if card_path:
                    c["img"], c["full"] = card_path, full_path
            break
    save_cars(cars)
    flash("Car updated.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/delete", methods=["POST"])
@admin_required
def admin_delete():
    car_id = int(request.form.get("id", 0))
    cars = [c for c in load_cars() if c.get("id") != car_id]
    save_cars(cars)
    flash("Car removed.")
    return redirect(url_for("admin"))


# ---- Admin: partners (add + delete) -----------------------------------------
@app.route(f"/{config.ADMIN_PATH}/partner/add", methods=["POST"])
@admin_required
def admin_partner_add():
    partners = load_partners()
    new_id = next_partner_id(partners)

    img = "assets/img/team/team-1.webp"   # sensible default if no photo is given
    photo = request.files.get("photo")
    if photo and photo.filename:
        p = process_partner_photo(photo, f"partner-{new_id}")
        if p:
            img = p

    order_raw = request.form.get("order", "").strip()
    try:
        order = int(order_raw)
    except ValueError:
        order = next_partner_order(partners)

    partners.append({
        "id":    new_id,
        "name":  request.form.get("name", "").strip(),
        "role":  request.form.get("role", "Partner").strip() or "Partner",
        "img":   img,
        "order": order,
    })
    partners.sort(key=lambda p: p.get("order", 999))
    save_partners(partners)
    flash("Partner added.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/partner/delete", methods=["POST"])
@admin_required
def admin_partner_delete():
    pid = int(request.form.get("id", 0))
    partners = [p for p in load_partners() if p.get("id") != pid]
    save_partners(partners)
    flash("Partner removed.")
    return redirect(url_for("admin"))


@app.route(f"/{config.ADMIN_PATH}/partner/update", methods=["POST"])
@admin_required
def admin_partner_update():
    """Save the inline edits (name, role, order) for one partner card."""
    pid = int(request.form.get("id", 0))

    order_raw = request.form.get("order", "").strip()
    try:
        order = int(order_raw)
    except ValueError:
        order = None

    partners = load_partners()
    for p in partners:
        if p.get("id") == pid:
            name = request.form.get("name", "").strip()
            role = request.form.get("role", "").strip()
            if name:
                p["name"] = name
            if role:
                p["role"] = role
            if order is not None:
                p["order"] = order
            break

    partners.sort(key=lambda p: p.get("order", 999))
    save_partners(partners)
    flash("Partner updated.")
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
