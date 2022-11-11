# 当我写下这段时，只有上帝和我明白我在做什么
# 现在只有上帝明白了
import os
import shutil
from threading import Lock
from typing import Any, Callable, ClassVar, Generic, Iterable, Literal, TypeVar

import yaml
from loguru import logger
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from typing_extensions import TypeVarTuple, Unpack

try:
  from yaml import CSafeDumper as SafeDumper, CSafeLoader as SafeLoader
except ImportError:
  logger.info("似乎没有安装libyaml，将使用纯Python的YAML解析器")
  from yaml import SafeDumper, SafeLoader


def encode(data: Any) -> Any:
  if data is None or isinstance(data, (str, int, float)):
    return data
  elif isinstance(data, dict):
    return {k: encode(v) for k, v in data.items()}
  elif isinstance(data, list):
    return [encode(v) for v in data]
  else:
    return encode(pydantic_encoder(data))


TModel = TypeVar("TModel", bound=BaseModel)
TParam = TypeVarTuple("TParam")
LoadHandler = Callable[[TModel | None, TModel, Unpack[TParam]], None]
Reloadable = Literal[False, "eager", "lazy"]


class BaseConfig(Generic[TModel, Unpack[TParam]]):
  category: ClassVar = "配置"
  all: ClassVar[list["BaseConfig"]] = []

  def __init__(self, model: type[TModel], reloadable: Reloadable = "lazy") -> None:
    self.model = model
    self.cache: dict[tuple[Unpack[TParam]], TModel] = {}
    self.reloadable: Reloadable = reloadable
    self.handlers: list[LoadHandler[TModel, Unpack[TParam]]] = []
    self.lock = Lock()
    self.all.append(self)

  def get_file(self, *args: Unpack[TParam]) -> str:
    raise NotImplementedError

  def __call__(self, *args: Unpack[TParam]) -> TModel:
    if args not in self.cache:
      with self.lock:  # Nonebot 的 run_sync 不在主线程
        if args not in self.cache:
          self.load(*args)
    return self.cache[args]

  def load(self, *args: Unpack[TParam]) -> None:
    if args in self.cache:
      old_config = self.cache[args]
    else:
      old_config = None
    file = self.get_file(*args)
    if os.path.exists(file):
      logger.info(f"加载{self.category}文件: {file}")
      with open(file) as f:
        self.cache[args] = self.model.parse_obj(yaml.load(f, SafeLoader))
    else:
      logger.info(f"{self.category}文件不存在: {file}")
      self.cache[args] = self.model()
    for handler in self.handlers:
      handler(old_config, self.cache[args], *args)

  def dump(self, *args: Unpack[TParam]) -> None:
    if args not in self.cache:
      return
    data = encode(self.cache[args].dict())
    file = self.get_file(*args)
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w") as f:
      yaml.dump(data, f, SafeDumper, allow_unicode=True)

  def onload(
    self
  ) -> "Callable[[LoadHandler[TModel, Unpack[TParam]]], LoadHandler[TModel, Unpack[TParam]]]":
    def decorator(  # 必须是 ForwardRef，否则会 KeyError: typing_extensions.Unpack[TParam]
      handler: "LoadHandler[TModel, Unpack[TParam]]"
    ) -> "LoadHandler[TModel, Unpack[TParam]]":
      self.handlers.append(handler)
      return handler
    return decorator

  def get_all(self) -> Iterable[tuple[Unpack[TParam]]]:
    raise NotImplementedError

  def load_all(self) -> None:
    for i in self.get_all():
      self.load(*i)

  def reload(self) -> None:
    if self.reloadable == "eager":
      for key in self.cache:
        self.load(*key)
    elif self.reloadable == "lazy":
      self.cache.clear()
    else:
      raise ValueError(f"{self} 不可重载")


class SharedConfig(BaseConfig[TModel]):
  base_dir: ClassVar = "configs"

  def __init__(self, name: str, model: type[TModel], reloadable: Reloadable = "lazy") -> None:
    super().__init__(model, reloadable)
    self.name = name

  def get_file(self) -> str:
    return f"{self.base_dir}/{self.name}.yaml"

  def get_all(self) -> Iterable[tuple[()]]:
    yield ()


class SharedState(SharedConfig[TModel]):
  category = "状态"
  base_dir = "states"


class GroupConfig(BaseConfig[TModel, int]):
  base_dir: ClassVar = "configs"

  def __init__(self, name: str, model: type[TModel], reloadable: Reloadable = "lazy") -> None:
    super().__init__(model, reloadable)
    self.name = name

  def get_file(self, group: int) -> str:
    file = f"{self.base_dir}/{self.name}/{group}.yaml"
    default_file = f"{self.base_dir}/{self.name}/default.yaml"
    if not os.path.exists(file) and os.path.exists(default_file):
      shutil.copy(default_file, file)
    return file

  def get_all(self) -> Iterable[tuple[int]]:
    from . import context
    for i in context.CONFIG().groups:
      yield i,


class GroupState(GroupConfig[TModel]):
  category = "状态"
  base_dir = "states"
