import pytest
import requests
import time
from subprocess import Popen
from signal import SIGINT
from pyattention.source import socketIO

@pytest.fixture()
def makeServer():
    p = Popen(['python', 'tests/socketIO_server.py'])
    time.sleep(1)  # Give the server time to start
    yield None
    p.send_signal(SIGINT)
    time.sleep(0.5)  # Give the server time to shutdown


def test_socketIO(makeServer):
    src = socketIO('http://localhost:20202')
    async def callback(data):
        await src.put(data)
    src.subscribe('pushState', handler=callback)
    src.emit('getState')
    retv = src.get()

    assert retv is not None, 'retv should have the return value but it was None instead'
    assert type(retv) is dict, 'retv should be a dict'
    assert retv.get('pushState') is not None, 'retv should contain pushState key'
    assert retv['pushState'].get('artist') == 'Lisa Hannigan', f'Received unexpected return value: {retv}'
