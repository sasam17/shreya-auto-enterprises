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

# ── FAIL-SAFE: never start a live site on the shipped default password ──────────
# If SHREYA_ADMIN_PASSWORD wasn't set, the admin would be protected by the public
# default "shreya2017" — i.e. not protected at all. Refuse to boot so the mistake is
# caught loudly at deploy time instead of silently shipping an open admin panel.
if config.PASSWORD_IS_DEFAULT:
    raise RuntimeError(
        "\n\n  REFUSING TO START — the admin password is still the built-in default.\n"
        "  Set a strong SHREYA_ADMIN_PASSWORD environment variable in your host's\n"
        "  dashboard, then restart. (See DEPLOYER.md.) This guard exists so the site\n"
        "  can never go live with an unprotected admin panel.\n"
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
