import asyncio
import threading


class status:
    SUCCESS = 200  # noqa: E221 OK
    OVERFLOW = 413  # noqa: E221 Payload too large
    FAILED = 500  # noqa: E221 Internal Server Error
    TIMEOUT = 505  # noqa: E221 Gateway Timeout
    NOSTATUS = 0  # noqa: E221 Message has no status
    detail = {
        SUCCESS: "Success",
        OVERFLOW: "Overflow",
        FAILED: "Failed",
        TIMEOUT: "Timeout",
        NOSTATUS: "No Status",
    }


class message:
    header = None
    footer = None
    data = None
    error = None
    status = 0
    MAXSIZE = 16384

    def __repr__(self):
        detail = status.detail.get(self.status, f"Unknown ({self.status})")
        msg = self.data or self.footer or self.header or ""
        if 200 <= self.status < 300:
            return f"[{detail}] {msg}"
        else:
            return f"[{detail}] {self.error}"


class threadloop(object):
    """
    Class to provide a loop contained within a thread
    """

    def __init__(self):
        # Initialize thread and async loop

        def run_loop(loop):
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                loop.close()

        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=run_loop, args=(self.loop,), daemon=True
        )
        self._thread.start()
