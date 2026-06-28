"""
Daraja Routes
-------------
Safaricom callback endpoint. Not authenticated by JWT.
Secured by IP whitelist + payload validation instead.
POST /api/daraja/callback
"""

from flask import Blueprint
from app.controllers.daraja_controller import DarajaController

daraja_bp = Blueprint("daraja", __name__, url_prefix="/api/daraja")


@daraja_bp.post("/callback")
def callback():
    return DarajaController.callback()
