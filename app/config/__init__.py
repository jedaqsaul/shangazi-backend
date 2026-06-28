from .development import DevelopmentConfig
from .production import ProductionConfig

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
