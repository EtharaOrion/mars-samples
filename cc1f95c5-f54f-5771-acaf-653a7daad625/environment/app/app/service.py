from app.core import config


def describe():
    return {
        "service": config.SERVICE_NAME,
        "revision": config.CONFIG_REVISION,
        "max_retries": config.MAX_RETRIES,
        "timeout_ms": config.TIMEOUT_MS,
    }


def enabled(flag):
    return flag in config.FEATURE_FLAGS
