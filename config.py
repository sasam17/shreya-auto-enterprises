"""
config.py — all the settings for the Shreya Auto web app live here in one place.

You normally only edit THIS file. Nothing here is complicated — they're just
values the app reads when it starts.

ON A WEB HOST (after deployment): do NOT put real passwords in this file (it can
end up in your code history). Instead set the matching ENVIRONMENT VARIABLE in
your host's dashboard — each setting below shows its variable name. An environment
variable, when present, overrides the value written here. See DEPLOY.md.
"""

import os


def _load_dotenv():
    """Load KEY=VALUE lines from a local, gitignored `.env` file into the environment.

    This lets you keep SECRETS (like the Gmail App Password) in a `.env` file that is
    NEVER committed — instead of typing them into this file, which IS committed to the
    public repo. On a real host you set real environment variables, so `.env` is unused.
    Copy `.env.example` to `.env` and fill it in. Existing real env vars always win.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_dotenv()


def _env(name, default):
    """Read an environment variable, falling back to the value written here."""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


# ── Admin login ──────────────────────────────────────────────────────────────
# The password to open the admin page where cars are added/removed.
# CHANGE THIS to something only you know before going live.
# Host override:  SHREYA_ADMIN_PASSWORD
ADMIN_PASSWORD = _env("SHREYA_ADMIN_PASSWORD", "shreya2017")

# The shipped default — the app REFUSES to run in production while this is still the
# password (wsgi.py raises on startup), so the site can never go live unprotected.
_DEFAULT_ADMIN_PASSWORD = "shreya2017"
PASSWORD_IS_DEFAULT = (ADMIN_PASSWORD == _DEFAULT_ADMIN_PASSWORD)

# The SECRET web address of the admin panel. Bots constantly scan sites for "/admin";
# giving the panel a non-obvious address means those scans hit a plain 404 and find
# nothing. You log in at  yourdomain.com/<this value> . Change it to anything you like
# (letters, numbers, hyphens) — and tell only the people who manage the site.
# Host override:  SHREYA_ADMIN_PATH
ADMIN_PATH = (_env("SHREYA_ADMIN_PATH", "office-2f9k7x").strip().strip("/") or "office-2f9k7x")

# Auto-logout: minutes of inactivity before an admin session expires and must log in
# again (so a browser left open on a shared computer doesn't stay logged in forever).
# Host override:  SHREYA_SESSION_TIMEOUT_MIN
SESSION_TIMEOUT_MIN = int(_env("SHREYA_SESSION_TIMEOUT_MIN", "30"))

# A random secret the app uses to keep you logged in. Leave the placeholder and
# the app will auto-generate a strong, stable key on first run (saved to the
# gitignored file .secret_key). On a host, set SHREYA_SECRET_KEY to a long random
# string instead — generate one with:
#     python -c "import secrets; print(secrets.token_hex(32))"
# Host override:  SHREYA_SECRET_KEY
SECRET_KEY = _env("SHREYA_SECRET_KEY", "change-this-to-a-long-random-string-9f3a7c2b18e4")

# Developer mode. TRUE locally (nicer error pages + auto-opens the browser).
# MUST be FALSE in production — wsgi.py forces it off automatically when a real
# web host loads the app, which also switches cookies to HTTPS-only.
# Host override:  SHREYA_DEBUG  (set to 0 in production)
DEBUG = _env("SHREYA_DEBUG", "1").strip().lower() in ("1", "true", "yes", "on")

# ── Email for inquiries (OPTIONAL) ───────────────────────────────────────────
# Every inquiry from the website is ALWAYS saved to data/inquiries.json so you
# never lose one. If you also want them emailed to you, fill these in.
# For a Gmail account you must create an "App Password" (Google Account →
# Security → App passwords) and paste it as MAIL_PASSWORD.
# Leave MAIL_USERNAME empty to turn email off (the site still works perfectly).
MAIL_SERVER   = _env("SHREYA_MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT     = int(_env("SHREYA_MAIL_PORT", "587"))
MAIL_USERNAME = _env("SHREYA_MAIL_USERNAME", "")    # e.g. "shreyaauto.enterprises@gmail.com"
MAIL_PASSWORD = _env("SHREYA_MAIL_PASSWORD", "")    # the 16-character Gmail App Password
MAIL_TO       = _env("SHREYA_MAIL_TO", "shreyaauto.enterprises@gmail.com")

# ── Image handling ───────────────────────────────────────────────────────────
# When you upload a car photo in the admin, the app shrinks + converts it to a
# fast WebP automatically. This is the max width it resizes large photos to.
IMAGE_MAX_WIDTH = int(_env("SHREYA_IMAGE_MAX_WIDTH", "1240"))

# ── Database ─────────────────────────────────────────────────────────────────
# Where all records (users, cars, partners, inquiries, reviews, buyers, sales,
# audit logs) are stored. The app is DUAL-ENGINE — the SAME code runs on either:
#
#   • SQLite  (default, local dev): a single file data/shreya.db — no server.
#   • MySQL   (production, e.g. PythonAnywhere): a real database server.
#
# The connection string is chosen in this order:
#   1. SHREYA_DATABASE_URL if set (full URL — simplest for PythonAnywhere), else
#   2. the individual MYSQL_* variables below (HOST/PORT/USER/PASSWORD/DB), else
#   3. the local SQLite file.
# Any DB password lives ONLY in .env or the host's settings — never in this file.
_DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "shreya.db")
_DEFAULT_DB = "sqlite:///" + _DB_PATH.replace("\\", "/")


def _build_database_url():
    """Pick the database connection string (see the ordered rules above)."""
    explicit = _env("SHREYA_DATABASE_URL", "")
    if explicit:
        return explicit
    host = _env("MYSQL_HOST", "")
    if host:
        port = _env("MYSQL_PORT", "3306")
        user = _env("MYSQL_USER", "root")
        pwd  = _env("MYSQL_PASSWORD", "")
        name = _env("MYSQL_DB", "shreya_db")
        # utf8mb4 = full Unicode incl. Nepali (Devanagari) and emoji.
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"
    return _DEFAULT_DB


DATABASE_URL = _build_database_url()

# Connection-pool tuning (used by db.py's create_engine). Sensible for a small
# hosted MySQL; harmless for SQLite. Overridable via env if ever needed.
DB_POOL_SIZE    = int(_env("SHREYA_DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(_env("SHREYA_DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(_env("SHREYA_DB_POOL_RECYCLE", "3600"))   # recycle conns hourly

# ── Superadmin bootstrap (RBAC) ──────────────────────────────────────────────
# On first run, if there are no user accounts yet, ONE superadmin is created from
# these values so you can log in. For safety the seeded account is flagged
# "must change password", so the very first login forces a new password — the
# default below is never a usable long-term password. Set real values in .env /
# host settings for production.
SUPERADMIN_USERNAME = _env("SHREYA_SUPERADMIN_USERNAME", "admin")
_DEFAULT_SUPERADMIN_PASSWORD = "admin123"
SUPERADMIN_PASSWORD = _env("SHREYA_SUPERADMIN_PASSWORD", _DEFAULT_SUPERADMIN_PASSWORD)
# Production must not boot on the built-in default superadmin password (wsgi.py enforces).
SUPERADMIN_IS_DEFAULT = (SUPERADMIN_PASSWORD == _DEFAULT_SUPERADMIN_PASSWORD)
