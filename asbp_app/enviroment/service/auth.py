import hashlib
import json
import sys
from base64 import b64encode, b64decode
from datetime import timedelta, datetime
from typing import Dict, Tuple, Union, Type

import pytz
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from asbp_app.enviroment.infrastructure.database.models import SystemUser, SystemUserSession, UserRole, UserRoleGroup
from sanic import Request
from tortoise.transactions import atomic
from web_foundation.environment.services.service import Service
from web_foundation.errors.io.http_auth import MissingAuthorizationCookie, AuthenticationFailed, ScopesFailed
from web_foundation.utils.crypto import BaseCrypto


class CookiesStruct:
    token: str
    session: int

    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.validate()

    def validate(self):
        # try:
        for cock in ["token", "session"]:
            if cock not in list(self.cookies.keys()):
                raise MissingAuthorizationCookie("Invalid cookies")
        if not self.cookies["session"].isdigit():
            raise AuthenticationFailed("Invalid cookies")
        self.token = self.cookies["token"]
        self.session = int(self.cookies["session"])
        # self.expire_at = datetime.strptime(self.cookies["expire_at"], self.time_format)


class AESCrypto(BaseCrypto):
    class DataStruct:
        __slots__ = ["cipher_text", "salt", "nonce", "tag"]

        def __init__(self, cipher_text, salt, nonce, tag):
            self.cipher_text = cipher_text
            self.salt = salt
            self.nonce = nonce
            self.tag = tag

        def decode(self):
            for var, val in self.__dict__().items():
                setattr(self, var, b64decode(val))

        def encode(self):
            encoding = sys.getdefaultencoding()
            for var, val in self.__dict__().items():
                setattr(self, var, b64encode(val).decode(encoding))

        def __dict__(self):
            return {"cipher_text": self.cipher_text,
                    "salt": self.salt,
                    "nonce": self.nonce,
                    "tag": self.tag}

        def __str__(self):
            return "\n".join([f"{k} : {v}" for k, v in self.__dict__().items()])

    _data_password: str
    _n_factor: int
    _block_size: int
    _threads_num: int
    _key_len: int

    def __init__(self, secret: str):
        super(AESCrypto, self).__init__()
        self._data_password = secret
        self._n_factor = 2 ** 14
        self._block_size = 8
        self._threads_num = 1
        self._key_len = 32

    def encrypt(self, plain_text: str) -> DataStruct:
        salt = get_random_bytes(AES.block_size)
        private_key = hashlib.scrypt(
            self._data_password.encode(), salt=salt, n=self._n_factor, r=self._block_size, p=self._threads_num,
            dklen=self._key_len)
        cipher_config = AES.new(private_key, AES.MODE_GCM)
        cipher_text, tag = cipher_config.encrypt_and_digest(bytes(plain_text, sys.getdefaultencoding()))
        return AESCrypto.DataStruct(cipher_text, salt, cipher_config.nonce, tag)

    def decrypt(self, aes_struct: DataStruct) -> str:
        aes_struct.decode()
        private_key = hashlib.scrypt(
            self._data_password.encode(), salt=aes_struct.salt, n=self._n_factor, r=self._block_size,
            p=self._threads_num,
            dklen=self._key_len)
        cipher = AES.new(private_key, AES.MODE_GCM, nonce=aes_struct.nonce)
        decrypted = cipher.decrypt_and_verify(aes_struct.cipher_text, aes_struct.tag)
        return decrypted

    @property
    def key_len(self):
        return self._key_len


class AuthService(Service):
    _crypto_algorithm: BaseCrypto
    _default_expire_time: int
    secret: str

    def __init__(self, crypto_secret: str, token_live_time: int = 84600):
        self._crypto_algorithm = AESCrypto(crypto_secret)
        self.secret = crypto_secret
        self.token_live_time = token_live_time

    @property
    def algorithm(self):
        return self._crypto_algorithm

    async def get_user(self, username: str, password: str) -> SystemUser:
        user = await SystemUser.get_or_none(username=username)
        if user is None or user.deleted:
            raise AuthenticationFailed(f"No user with username: {username}")
        if not self._crypto_algorithm.verify_password(password, user.password, user.salt):
            raise AuthenticationFailed(f"Wrong password")
        return user

    async def generate_token(self, payload: str) -> AESCrypto.DataStruct:
        return self._crypto_algorithm.encrypt(payload)

    @atomic()
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

    @atomic()
    async def validate_request(self, request: Request,
                               session_model: Type[SystemUserSession]) -> \
            Tuple[SystemUser, Dict, SystemUserSession]:
        if not request.cookies:
            raise AuthenticationFailed("Can't find cookies")
        cok = CookiesStruct(request.cookies)
        session = await session_model.get_or_none(id=cok.session).select_related("user")
        if not session:
            raise AuthenticationFailed("Session not found, or already expired")
        if session.expire_time <= datetime.now(tz=pytz.UTC):
            raise AuthenticationFailed("Session expired")
        aes = AESCrypto.DataStruct(cok.token,
                                   session.salt,
                                   session.nonce,
                                   session.tag)
        try:
            payload_str = self._crypto_algorithm.decrypt(aes)
        except Exception as e:
            raise AuthenticationFailed("Can't authorize with this cookies")
        payload = json.loads(payload_str)
        user = await session.user.prefetch_related("role_group__roles")
        user.last_active = datetime.now().astimezone()
        await user.save()
        return user, payload, session

    async def check_scopes(self, request: Request, user: SystemUser) -> None:
        for user_role in user.role_group.roles:
            if user_role.name == request.route.handler.__name__:
                return
            role_postfix = "__read" if request.method.lower() == "get" else "__edit"
            role_name = request.route.handler.__name__ + role_postfix
            if user_role.name == role_name:
                return
        if not await UserRole.exists(name__contains=request.route.handler.__name__):
            return
        raise ScopesFailed("Permission denied")
