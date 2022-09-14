from typing import Optional

from pydantic import BaseSettings, BaseModel
from web_foundation.kernel.configuration import DbConfig
from web_foundation.utils.logger import LoggerSettings


class ServerConfig(BaseModel):
    host: str
    port: int
    file_store_path: str
    static_url: str
    static_dir: str


class StreamingConf(BaseModel):
    listen_timeout: float
    ping_timeout: float


class MasterSlaveConf(BaseModel):
    master: bool
    master_ip: Optional[str]
    sync_period: Optional[int]  # in minute or seconds?


class Config(BaseSettings):
    app_name: str
    streaming: StreamingConf
    database: DbConfig
    server: ServerConfig
    logger: LoggerSettings
