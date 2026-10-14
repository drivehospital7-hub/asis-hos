import logging

from waitress import serve

from app import create_app
from app.constants.server import (
    WAITRESS_CHANNEL_TIMEOUT,
    WAITRESS_CLEANUP_INTERVAL,
    WAITRESS_CONNECTION_LIMIT,
    WAITRESS_MAX_REQUEST_BODY_SIZE,
    WAITRESS_THREADS,
)
from config.prod import ProdConfig

logger = logging.getLogger(__name__)


def main():
    app = create_app(ProdConfig)

    logger.info(
        "Starting production server on %s:%s (threads=%d)",
        ProdConfig.HOST,
        ProdConfig.PORT,
        WAITRESS_THREADS,
    )
    print(f"Starting production server on {ProdConfig.HOST}:{ProdConfig.PORT}")
    print("Access from network at: http://<your-ip>:{}/".format(ProdConfig.PORT))

    serve(
        app,
        host=ProdConfig.HOST,
        port=ProdConfig.PORT,
        threads=WAITRESS_THREADS,
        connection_limit=WAITRESS_CONNECTION_LIMIT,
        channel_timeout=WAITRESS_CHANNEL_TIMEOUT,
        cleanup_interval=WAITRESS_CLEANUP_INTERVAL,
        max_request_body_size=WAITRESS_MAX_REQUEST_BODY_SIZE,
    )


if __name__ == "__main__":
    main()
