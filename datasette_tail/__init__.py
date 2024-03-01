from datasette import hookimpl, Forbidden, Response
import dictdiffer
import json
from markupsafe import escape


@hookimpl
def database_actions(datasette, actor, database):
    async def inner():
        if await datasette.permission_allowed(
            actor, "view-database", resource=database
        ):
            return [
                {
                    "href": datasette.urls.database(database) + "/-/tail",
                    "label": "Tail this database",
                }
            ]

    return inner


async def _shared(datasette, request):
    database = request.url_vars["database"]
    if not await datasette.permission_allowed(
        request.actor, "view-database", resource=database
    ):
        raise Forbidden("view-database permission is required")

    datasette._tail_state = getattr(datasette, "_tail_state", None) or {}
    db = datasette.get_database(database)
    previous_state = datasette._tail_state.get(database) or {}
    tables = await db.table_names()
    new_state = {
        table: [
            dict(row)
            for row in (await db.execute('select * from "{}"'.format(table))).rows
        ]
        for table in tables
    }
    datasette._tail_state[database] = new_state
    return list(dictdiffer.diff(previous_state, new_state, expand=True))


async def tail_database(datasette, request):
    diffs = await _shared(datasette, request)
    return Response.html(
        "<pre>{}</pre>".format(escape(json.dumps(diffs, indent=2, default=repr)))
    )


async def tail_database_json(datasette, request):
    return Response.json(await _shared(datasette, request))


@hookimpl
def register_routes():
    return [
        (r"^/(?P<database>[^/]+)/-/tail$", tail_database),
        (r"^/(?P<database>[^/]+)/-/tail\.json$", tail_database_json),
    ]
