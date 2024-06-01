from typing import Generic, TypedDict, TypeVar

from pydantic import BaseModel, SecretStr
from typing_extensions import NotRequired

from .. import configs

__all__ = ['ApiError', 'ApiResult', 'CONFIG', 'Config', 'get_cookie']


class Config(BaseModel):
  cookie: SecretStr = SecretStr("")


CONFIG = configs.SharedConfig("bilibili_auth", Config)
TData = TypeVar("TData")


def get_cookie() -> str:
  return CONFIG().cookie.get_secret_value()


class ApiResult(TypedDict, Generic[TData]):
  code: int
  message: str
  ttl: int
  data: NotRequired[TData]


class ApiError(Exception):
  def __init__(self, code: int, message: str) -> None:
    super().__init__(f"{code}: {message}")
    self.code = code
    self.message = message

  def __repr__(self) -> str:
    return f"ApiError(code={self.code!r}, message={self.message!r})"
  
  @staticmethod
  def check(result: ApiResult[TData]) -> TData:
    if result["code"] != 0:
      raise ApiError(result["code"], result["message"])
    return result["data"]  # type: ignore
