"""Entry point of the worker. Run with: python -m gridcheck.worker"""

import logging
import signal
import threading
from types import FrameType

from gridcheck import config
from gridcheck.worker.loop import run_worker

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)
    stop = threading.Event()

    def request_stop(signum: int, frame: FrameType | None) -> None:
        log.info(
            "%s received, stopping after the current job", signal.strsignal(signum)
        )
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    run_worker(config.db_uri(), stop)


if __name__ == "__main__":
    main()
