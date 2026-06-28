"""
Production WSGI Entry Point
----------------------------
Used by Gunicorn in production.

Start command:
    gunicorn wsgi:app --workers 4 --bind 0.0.0.0:5000 --timeout 120

Workers formula: (2 × CPU cores) + 1
  2 core server → 5 workers
  4 core server → 9 workers
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app(config_name="production")
