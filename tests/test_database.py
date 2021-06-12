from pyattention.source import database


def test_db():
    src = database("sqlite+aiosqlite:///tests/reference/test.db")
    src.add("Select * from beer", repeat=1)
    d = src.get()
    assert (
        d["Id"] == 1
        and d["Name"] == "Golden Ale"
        and d["Desc"] == "A light example of the Golden Ale Style"
    ), "Database did not return expected values"
