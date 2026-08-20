"""
passenger_wsgi.py — cPanel Phusion Passenger entry point.

cPanel's "Setup Python App" runs your Flask application using Phusion Passenger.
Passenger imports the `application` object from this file.
"""

import os
import sys

# Add project root directory to sys.path so modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Load local .env file variables if present ──
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except Exception:
        pass

# Force production settings
os.environ.setdefault("SHREYA_DEBUG", "0")

# Import the WSGI application object from wsgi.py
from wsgi import application
