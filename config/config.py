from orjson import loads
from pydantic import BaseModel, DirectoryPath


class RedisConf(BaseModel):
    url: str
    max_connections: int
    poll_timeout: float


class ReportConf(BaseModel):
    name: str
    path: DirectoryPath


class StreamingConf(BaseModel):
    listen_timeout: float
    ping_timeout: float


class Config(BaseModel):
    some_conf: str
    redis: RedisConf
    streaming: StreamingConf
    reports: list[ReportConf]


def get_config(json_conf_path: str) -> Config:
    with open(json_conf_path, "r") as _json_file:
        return Config(**loads(_json_file.read()))
