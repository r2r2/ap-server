import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Tuple, Union

import pytz
from sanic import HTTPResponse, Request, Sanic
from sanic import json as json_response
from sanic.views import HTTPMethodView
from tortoise.transactions import atomic

import settings
from core.dto import service, validate
from core.errors.auth_errors import (AuthenticationFailed,
                                     MissingAuthorizationCookie, ScopesFailed)
from core.utils.crypto import AESCrypto, BaseCrypto
from infrastructure.database.models import (EnableScope, Role, SystemUser,
                                            SystemUserSession)


def generate_auth_resp(auth, session, token_data, scopes, username):
    expire = session.expire_time.strftime(auth.time_format)
    resp = json_response({
        "token": token_data.cipher_text,
        "session": session.id,
        "expire_at": expire,
        "scopes": scopes,
        "username": username
    })
    resp.cookies["token"] = token_data.cipher_text
    resp.cookies["session"] = str(session.id)
    resp.cookies["expire_at"] = str(expire)
    return resp


class UserAuthController(HTTPMethodView):

    async def post(self, request: Request) -> HTTPResponse:
        dto: service.Auth.LoginDto = validate(service.Auth.LoginDto, request)
        auth: Auth = request.app.ctx.auth
        user = await auth.get_user(dto.username, dto.password)
        payload = user.to_dict()
        scopes = await self.get_routes_id(payload["scopes"])
        token_data = await auth.generate_token(json.dumps(payload))
        session = await auth.create_session(user, request.headers.get("user-agent"), token_data)
        return generate_auth_resp(auth, session, token_data, scopes, dto.username)

    async def get_routes_id(self, payload: list[str]):
        scopes = [role.id for role in await Role.filter(name__in=payload)]
        routes_id = [route.id for route in await EnableScope.filter(scopes__id__in=scopes).distinct()]
        return routes_id


class CookiesStruct:
    token: str
    session: int
    expire_at: datetime

    def __init__(self, cookies: dict, time_format: str):
        self.cookies = cookies
        self.time_format = time_format
        self.validate()

    def validate(self):
        if ["token", "session", "expire_at"].sort() != list(self.cookies.keys()).sort():
            raise MissingAuthorizationCookie("Invalid cookies")
        if not self.cookies["session"].isdigit():
            raise AuthenticationFailed("Invalid cookies")
        self.token = self.cookies["token"]
        self.session = int(self.cookies["session"])
        self.expire_at = datetime.strptime(self.cookies["expire_at"], self.time_format)


class Auth:
    _crypto_algorithm: BaseCrypto
    _default_expire_time: int
    _time_format = "%d-%m-%Y %H:%M:%S"

    def __init__(self, app: Sanic):
        self._crypto_algorithm = AESCrypto(app.config.FORWARDED_SECRET)

    @property
    def time_format(self):
        return self._time_format

    @property
    def algorithm(self):
        return self._crypto_algorithm

    async def get_user(self, username: str, password: str) -> SystemUser:
        user = await SystemUser.get_or_none(username=username).prefetch_related("scopes")
        if user is None or user.deleted:
            raise AuthenticationFailed(f"No user with username: {username}")
        if not self._crypto_algorithm.verify_password(password, user.password, user.salt):
            raise AuthenticationFailed(f"Wrong password")
        return user

    async def generate_token(self, payload: str) -> AESCrypto.DataStruct:
        return self._crypto_algorithm.encrypt(payload)

    @atomic(settings.CONNECTION_NAME)
    async def create_session(self, user: SystemUser, user_agent: str,
                             aes_token_data: AESCrypto.DataStruct) -> SystemUserSession:
        if user.expire_session_delta == 0:
            expire_at = datetime.max
        else:
            expire_at = datetime.now().astimezone() + timedelta(seconds=user.expire_session_delta)
        aes_token_data.encode()
        session = await SystemUserSession.create(user=user,
                                                 user_agent=user_agent,
                                                 last_online=datetime.now().astimezone(),
                                                 created_at=datetime.now().astimezone(),
                                                 expire_time=expire_at,
                                                 salt=aes_token_data.salt,
                                                 nonce=aes_token_data.nonce,
                                                 tag=aes_token_data.tag
                                                 )

        return session

    @atomic(settings.CONNECTION_NAME)
    async def validate_request(self, request: Request, session_model: SystemUserSession) -> \
            Tuple[SystemUserSession, Dict]:
        if not request.cookies:
            raise AuthenticationFailed("Can't find cookies")
        cok = CookiesStruct(request.cookies, self._time_format)
        session = await session_model.get_or_none(id=cok.session)
        if not session:
            raise AuthenticationFailed("Session not found, or already expired")
        if session.expire_time <= datetime.now(tz=pytz.UTC):
            raise AuthenticationFailed("Session expired")
        aes = AESCrypto.DataStruct(cok.token,
                                   session.salt,
                                   session.nonce,
                                   session.tag)
        payload_str = self._crypto_algorithm.decrypt(aes)
        payload = json.loads(payload_str)
        user = await session.user.prefetch_related("scopes")
        return user, payload

    async def check_scopes(self, user_scopes: list[str], target_scopes: Union[list[str], str]) -> None:
        if isinstance(target_scopes, list):
            route_scope = set(target_scopes)
        elif isinstance(target_scopes, str):
            route_scope = {target_scopes}
        else:
            raise ScopesFailed("Permission denied")
        if not len(route_scope.intersection(user_scopes)) > 0:
            raise ScopesFailed("Permission denied")


def init_auth(app: Sanic):
    app.ctx.auth = Auth(app)
    app.add_route(UserAuthController.as_view(), "/auth")


def protect(retrive_user: bool = True):
    def called(method):
        @wraps(method)
        async def func(*args, **kwargs):
            cls = args[0]
            initial_args = args
            request = args[1]
            user, _ = await request.app.ctx.auth.validate_request(request, SystemUserSession)
            await request.app.ctx.auth.check_scopes([i.name for i in user.scopes], cls.enabled_scopes)
            if retrive_user:
                initial_args += (user,)
            return await method(*initial_args, **kwargs)

        return func

    return called
