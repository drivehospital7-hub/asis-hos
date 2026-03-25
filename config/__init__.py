from config.dev import DevConfig

def get_config(env=None):
    configs = {
        "development": DevConfig,
        "prod": ProdConfig,
        "production": ProdConfig,
    }
    if env is None:
        env = "development"
    return configs.get(env, DevConfig)
