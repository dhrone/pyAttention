# parser.py
from pyattention.exception import ParserException

"""
parser module

parsers are functions that accept a message and some optional arguments and return
a scalar, list, or dictionary that represents the data contained within the message.

If they encounter a message that contains input they cannot parse, they must throw
a ParserException exception.
"""


def kvp(msg, separator=":"):
    if type(msg) is str:
        msg = msg.strip().split("\n")

    lnum = 0
    d = {}
    try:
        for line in msg:
            k, v = line.split(separator, 1)
            d[k.strip()] = v.strip()
            lnum += 1
        if len(d) == 0:
            return None
        return d
    except Exception as ex:
        raise ParserException(f"kvp unable to parse line {lnum}: {ex}", msg)


def listOfKvp(msg, separator=":", startingKey=None):
    if type(msg) is str:
        msg = msg.strip().split("\n")
    ls = []
    d = {}
    lnum = 0
    try:
        for line in msg:
            k, v = line.split(separator, 1)
            if k.strip() == startingKey:
                if d:
                    ls.append(d)
                d = {}
            d[k.strip()] = v.strip()
            lnum += 1
        if d:
            ls.append(d)
        if len(ls) == 0:
            return None
        return ls
    except Exception as ex:
        raise ParserException(
            f"listOfKvp unable to parse line {lnum}: {ex}", msg
        )
