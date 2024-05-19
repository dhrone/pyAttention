from pyAttention.util import message


def test_util():
    msg = message()
    msg.data = {"a": 1}
    msg.status = 200

    res = repr(msg)
    assert res == "[Success] {'a': 1}", "Unexpected success message"

    msg.status = 505
    msg.error = "Too long"
    res = repr(msg)
    assert res == "[Timeout] Too long", "Unexpected error message"
