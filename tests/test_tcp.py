import time
from signal import SIGINT
from subprocess import Popen

import pytest
import requests

from pyattention import parser
from pyattention.source import tcp

port = 20204


@pytest.fixture()
def makeServer():
    p = Popen(["python", "tests/rss_server.py", str(port)])
    time.sleep(1)  # Give the server time to start
    yield None
    p.send_signal(SIGINT)
    time.sleep(0.5)  # Give the server time to shutdown


def test_tcp(makeServer):
    print("Starting Test")
    src = tcp(host="localhost", port=port)

    async def callback():
        await src.write("HEAD /\n\n")
        header = await src.readline()
        lines = []
        while True:
            line = await src.readline()
            line = line.strip()
            if len(line) == 0:
                break
            lines.append(line)
        data = parser.kvp(lines)
        await src.put(data)

    src.poll(handler=callback, repeat=1)
    retv = src.get()

    assert (
        retv is not None
    ), "retv should have the return value but it was None instead"
    assert type(retv) is dict, f"retv should be a dict: {retv}"
    assert "Content-Length" in retv, f"Content-Length key not found: {retv}"
    assert (
        retv["Content-Length"] == "1655"
    ), f"Content length was an unexpected value.  Expected '1655' but got {retv['Content-Length']}"

    src.poll(handler=callback, repeat=1)
    time.sleep(0.01)
    src.clear()
    retv = src.get()
    assert retv is None, f"After clear get should return None: {retv}"

    src.shutdown()
    try:
        src.checkAlive()
    except Exception as ex:
        assert (
            ex.__class__.__name__ == "RuntimeError"
        ), "After shutdown, shouldn't be alive"
