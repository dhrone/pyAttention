import pytest
from pyattention.parser import kvp, listOfKvp
from pyattention.exception import ParserException


def test_kvp():
    msg = "test:1\n" "test2:2"
    val = {"test": "1", "test2": "2"}
    res = kvp(msg)
    assert res == val, f"Should have been equal: {res} != {val}"

    msg = "test~1\n" "test2~2"
    val = {"test": "1", "test2": "2"}
    res = kvp(msg, "~")
    assert res == val, f"Should have been equal: {res} != {val}"


def test_kvp_fail():
    msg = ("test:1\n", "test2")
    with pytest.raises(ParserException):
        res = kvp(msg)


def test_listOfKvp():
    msg = ("test1:1\n", "test2:2\n", "test1:A\n", "test2:B")
    val = [{"test1": "1", "test2": "2"}, {"test1": "A", "test2": "B"}]
    res = listOfKvp(msg, startingKey="test1")

    assert type(res) is list, f"Result should have been list: {type(res)}"
    assert len(res) == 2, f"Result should have had two entries: {len(res)}"
    assert (
        res[0] == val[0]
    ), f"First result didn't match expected value: {res[0]} != {val[0]}"
    assert (
        res[1] == val[1]
    ), f"Second result didn't match expected value: {res[1]} != {val[1]}"


def test_listOfKvpFail():
    msg = "test1:1\n" "test2:2\n" "test1A\n" "test2:B"
    with pytest.raises(ParserException):
        res = listOfKvp(msg)
