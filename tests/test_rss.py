import pytest
import requests
import time
from subprocess import Popen
from signal import SIGINT
from pyattention.source import rss

port = 20203


@pytest.fixture()
def makeServer():
    p = Popen(["python", "tests/rss_server.py", str(port)])
    time.sleep(1)  # Give the server time to start
    yield None
    p.send_signal(SIGINT)
    time.sleep(0.5)  # Give the server time to shutdown


def test_rss(makeServer):
    global retv
    src = rss()
    src.add(f"http://localhost:{port}/", repeat=1)
    retv = src.get()

    assert (
        retv is not None
    ), "retv should have the return value but it was None instead"
    assert type(retv) is dict, "retv should be a dict"
    assert "data" in retv, "Contains data key"
    assert retv["data"][0]["title"][0:8] == "Saturday"
