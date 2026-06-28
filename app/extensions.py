"""
Extensions Module
-----------------
All Flask extension instances are created here and imported
wherever needed. This prevents circular imports by keeping
initialization separate from the app factory.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
