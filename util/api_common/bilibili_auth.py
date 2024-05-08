from pydantic import BaseModel, SecretStr

from .. import configs

__all__ = ["Config", "CONFIG", "get_cookie"]


class Config(BaseModel):
  cookie: SecretStr = SecretStr("")


CONFIG = configs.SharedConfig("bilibili_auth", Config)


def get_cookie() -> str:
  return CONFIG().cookie.get_secret_value()
