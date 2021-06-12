from pyattention.source import system
from pyattention.collection import collection

def test_collection():
    col = collection()
    src = system(loop=col.tloop)
    col.register('sys1', src)
    src = system(loop=col.tloop)
    col.register('sys2', src)
    res = {}
    ans = col.get(1)
    assert type(ans) is dict, f'Did not receive a valid message on attempt 1: {ans}'
    assert len(ans.keys()) != 1, f'Received an invalid number of messages: {len(ans.keys())}'
    res[list(ans.keys())[0]] = ans[list(ans.keys())[0]]

    ans = col.get(1)
    assert type(ans) is dict, f'Did not receive a valid message on attempt 2: {ans}'
    assert len(ans.keys()) != 1, f'Received an invalid number of messages: {len(ans.keys())}'
    res[list(ans.keys())[0]] = ans[list(ans.keys())[0]]

    assert 'sys1' in res, f'Did not receive message from sys1: {res}'
    assert 'sys2' in res, f'Did not receive message from sys2: {res}'

    assert type(col['sys1']) is dict, 'Test getitem failed'
    assert len(col) == 2, f'Test len failed.  Expected value was 2: {len(vol)}'

    col.shutdown()
    try:
        col.checkAlive()
    except Exception as ex:
        assert ex.__class__.__name__ == 'RuntimeError', 'col should not still be alive'

    try:
        src.checkAlive()
    except Exception as ex:
        assert ex.__class__.__name__ == 'RuntimeError', 'src should not still be alive'
