from sanic import Request


async def get_limit_offset(request: Request) -> tuple[int, int]:
    """When passing limit=0, in SQL this limit will be omitted."""
    limit = request.args.get("limit")
    offset = request.args.get("offset")
    limit = int(limit) if limit and limit.isdigit() else 0
    offset = int(offset) if offset and offset.isdigit() else 0
    return limit, offset
