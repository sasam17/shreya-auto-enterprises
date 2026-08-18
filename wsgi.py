"""
wsgi.py — the production entry point.

Real web hosts load the app from HERE, never by running app.py. Examples:

    PythonAnywhere : point the Web tab's WSGI config at this file's `application`
    gunicorn       : gunicorn wsgi:application            (Linux hosts: Render, Railway…)
    waitress       : waitress-serve --port=8000 wsgi:application   (Windows / any OS)

Loading the app through this file forces SHREYA_DEBUG=0 BEFORE the app is imported,
so production automatically gets: no debug error pages, and HTTPS-only login cookies —
even if you forget to set anything. See DEPLOY.md for the full walkthrough.
"""

import os

# Force production settings before importing the app (config.py reads this on import).
os.environ.setdefault("SHREYA_DEBUG", "0")

import config  # noqa: E402  (reads the env defaults set above)

# ── FAIL-SAFE: never start a live site on the shipped default superadmin password ──
# The admin panel now uses per-user logins; the first superadmin is seeded from
# SHREYA_SUPERADMIN_PASSWORD. If that's still the built-in default "admin123", anyone
# could log in before the owner does — so refuse to boot in production until it's set.
if config.SUPERADMIN_IS_DEFAULT:
    raise RuntimeError(
        "\n\n  REFUSING TO START — the superadmin password is still the built-in default.\n"
        "  Set a strong SHREYA_SUPERADMIN_PASSWORD environment variable in your host's\n"
        "  dashboard, then restart. (See DEPLOYER.md.) This guard exists so the site\n"
        "  can never go live with a guessable admin login.\n"
    )

from app import app as application  # noqa: E402  (must come after the checks above)


if __name__ == "__main__":
    # `python wsgi.py` runs a small real production server (waitress) if it's installed,
    # otherwise falls back to Flask's built-in server. Handy for a local production test.
    port = int(os.environ.get("SHREYA_PORT", "8000"))
    try:
        from waitress import serve
        print(f"Serving with waitress on http://0.0.0.0:{port}")
        serve(application, host="0.0.0.0", port=port)
    except ImportError:
        print("waitress not installed — using Flask's server. (pip install waitress)")
        application.run(host="0.0.0.0", port=port)
