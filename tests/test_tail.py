from datasette.app import Datasette
import pytest


@pytest.mark.asyncio
async def test_tail_database():
    ds = Datasette()
    db = ds.add_memory_database("tail")
    await db.execute_write("create table foo (id primary key, name text)")
    await db.execute_write("insert into foo (name) values ('Krishna')")
    response = await ds.client.get("/tail/-/tail.json")
    assert response.status_code == 200
    assert response.json() == [
        ["add", "", [["foo", [{"id": None, "name": "Krishna"}]]]]
    ]
    # Polling again should return nothing
    response2 = await ds.client.get("/tail/-/tail.json")
    assert response2.json() == []
    # Now insert a row and poll again
    await db.execute_write("insert into foo (name) values ('Troy')")
    response3 = await ds.client.get("/tail/-/tail.json")
    assert response3.json() == [["add", "foo", [[1, {"id": None, "name": "Troy"}]]]]
    # Finally check that the HTML page works
    response3 = await ds.client.get("/tail/-/tail")
    assert response3.headers["content-type"] == "text/html; charset=utf-8"
    assert response3.text == "<pre>[]</pre>"


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", (False, True))
async def test_permissions(allowed):
    ds = Datasette(config={"databases": {"tail2": {"allow": allowed}}})
    ds.add_memory_database("tail2")
    for path in ("/tail2/-/tail", "/tail2/-/tail.json"):
        response = await ds.client.get(path)
        if allowed:
            assert response.status_code == 200
        else:
            assert response.status_code == 403
