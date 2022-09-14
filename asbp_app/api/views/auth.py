import json
from typing import Dict

import sanic
from sanic_ext.extensions.openapi.builders import OperationStore
from web_foundation.environment.workers.web.ext.request_handler import InputContext
from web_foundation.errors.app.application import InconsistencyError


def auth_response_fabric(handler_resp: Dict):
    user = handler_resp.get("user")
    session = handler_resp.get("session")
    token_data = handler_resp.get("token_data")
    resp = sanic.response.json(
        {"token": token_data.cipher_text, "session": session.id, "user_id": str(user.id)})
    resp.cookies["token"] = token_data.cipher_text
    resp.cookies["session"] = str(session.id)
    return resp


async def user_auth_handler(ctx: InputContext, container):
    response = {"user": await container.auth_service.get_user(ctx.dto.username, ctx.dto.password)}
    payload = response["user"].to_dict()
    response["token_data"] = await container.auth_service.generate_token(json.dumps(payload))
    response["session"] = await container.auth_service.create_session(response["user"],
                                                                      ctx.request.headers.get("user-agent"),
                                                                      response["token_data"])
    return response


OperationStore()[user_auth_handler].responses["200"] = {"headers": {"Set-Cookie": {"schema": {
    "type": "string"},
    "description": "Set token and session"}}}

