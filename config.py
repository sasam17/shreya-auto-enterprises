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
# Where structured records (inquiries, reviews, car sales / buyers) are stored.
# Default: a local SQLite file at data/shreya.db — no server, no password needed.
# For a hosted MySQL database instead, set ONE environment variable:
#   SHREYA_DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME
# (Keep that URL — it contains the DB password — only in .env or the host's
#  settings, never written in this committed file.)
# Host override:  SHREYA_DATABASE_URL
_DB_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "shreya.db")
_DEFAULT_DB = "sqlite:///" + _DB_PATH.replace("\\", "/")
DATABASE_URL = _env("SHREYA_DATABASE_URL", _DEFAULT_DB)
