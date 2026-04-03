from config.dev import DevConfig
from config.prod import ProdConfig


def get_config(env=None):
    """Get configuration by environment name."""
    configs = {
        "development": DevConfig,
        "dev": DevConfig,
        "prod": ProdConfig,
        "production": ProdConfig,
    }
    if env is None:
        env = "development"
    return configs.get(env, DevConfig)
