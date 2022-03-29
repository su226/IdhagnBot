from typing import Any, ClassVar, Type, TypeVar
from pydantic import BaseModel, Field, PrivateAttr
from pydantic.json import pydantic_encoder
from loguru import logger
import os
import yaml

__all__ = ["BaseModel", "BaseConfig", "BaseState", "Field", "PrivateAttr"]

def encode(data: Any):
  if data is None or isinstance(data, (str, int, float, bool)):
    return data
  elif isinstance(data, dict):
    return {k: encode(v) for k, v in data.items()}
  elif isinstance(data, list):
    return [encode(v) for v in data]
  else:
    return encode(pydantic_encoder(data))

TSelf = TypeVar("TSelf", bound="BaseConfig")
class BaseConfig(BaseModel):
  __state__: ClassVar[bool] = False
  __path__: ClassVar[str] = ""
  __file__: ClassVar[str] = ""

  @classmethod
  def __get_info(cls) -> tuple[str, str]:
    name = "状态" if cls.__state__ else "配置"
    if cls.__path__:
      file = cls.__path__
    elif cls.__file__:
      file = ("states" if cls.__state__ else "configs") + f"/{cls.__file__}.yaml"
    else:
      raise RuntimeError("BaseConfig 的 __file__ 和 __path__ 必须要指定一个")
    return name, file 

  @classmethod
  def load(cls: Type[TSelf]) -> "TSelf":
    name, file = cls.__get_info()
    try:
      if os.path.exists(file):
        with open(file) as f:
          return cls.parse_obj(yaml.load(f, yaml.CLoader))
      else:
        logger.info(f"{name}文件不存在: {file}")
    except:
      logger.opt(exception=True).warning(f"无法读取{name}：{file}")
    return cls()

  def dump(self):
    name, file = self.__get_info()
    data = encode(self.dict())
    try:
      with open(file, "w") as f:
        yaml.dump(data, f, yaml.CDumper, allow_unicode=True)
    except:
      logger.opt(exception=True).warning(f"无法记录{name}：{file}")

class BaseState(BaseConfig):
  __state__ = True
