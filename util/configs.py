# 当我写下这段时，只有上帝和我明白我在做什么
# 现在只有上帝明白了
import os
import shutil
from dataclasses import dataclass
from threading import Lock
from typing import (
  Any, Callable, ClassVar, Dict, Generic, Iterable, List, Literal, Optional, Tuple, Type, TypeVar,
)

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
  elif isinstance(data, (list, tuple, set, frozenset)):
    return [encode(v) for v in data]
  else:
    return encode(pydantic_encoder(data))


TModel = TypeVar("TModel", bound=BaseModel)
TParam = TypeVarTuple("TParam")
LoadHandler = Callable[[Optional[TModel], TModel, Unpack[TParam]], None]
Reloadable = Literal[False, "eager", "lazy"]


@dataclass
class CacheItem(Generic[TModel]):
  item: TModel
  need_reload: bool = False


class BaseConfig(Generic[TModel, Unpack[TParam]]):
  category: ClassVar = "配置"
  all: ClassVar[List["BaseConfig[Any, Unpack[Tuple[Any, ...]]]"]] = []

  def __init__(self, model: Type[TModel], reloadable: Reloadable = "lazy") -> None:
    self.model = model
    self.cache: Dict[Tuple[Unpack[TParam]], CacheItem[TModel]] = {}
    self.reloadable: Reloadable = reloadable
    self.handlers: List[LoadHandler[TModel, Unpack[TParam]]] = []
    self.lock = Lock()
    self.all.append(self)

  def get_file(self, *args: Unpack[TParam]) -> str:
    raise NotImplementedError

  def __call__(self, *args: Unpack[TParam]) -> TModel:
    if args not in self.cache or self.cache[args].need_reload:
      with self.lock:  # Nonebot 的 run_sync 不在主线程
        if args not in self.cache or self.cache[args].need_reload:
          self.load(*args)
    return self.cache[args].item

  def load(self, *args: Unpack[TParam]) -> None:
    file = self.get_file(*args)
    if os.path.exists(file):
      logger.info(f"加载{self.category}文件: {file}")
      with open(file) as f:
        new_config = self.model.model_validate(yaml.load(f, SafeLoader))
    else:
      logger.info(f"{self.category}文件不存在: {file}")
      new_config = self.model()
    if args not in self.cache:
      old_config = None
      self.cache[args] = CacheItem(new_config)
    else:
      old_config = self.cache[args].item
      self.cache[args].item = new_config
    for handler in self.handlers:
      handler(old_config, new_config, *args)

  def dump(self, *args: Unpack[TParam]) -> None:
    if args not in self.cache:
      return
    data = encode(self.cache[args].item.model_dump())
    file = self.get_file(*args)
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w") as f:
      yaml.dump(data, f, SafeDumper, allow_unicode=True)

  def onload(
    self,
  ) -> "Callable[[LoadHandler[TModel, Unpack[TParam]]], LoadHandler[TModel, Unpack[TParam]]]":
    def decorator(  # 必须是 ForwardRef，否则会 KeyError: typing_extensions.Unpack[TParam]
      handler: "LoadHandler[TModel, Unpack[TParam]]",
    ) -> "LoadHandler[TModel, Unpack[TParam]]":
      self.handlers.append(handler)
      return handler
    return decorator

  def get_all(self) -> Iterable[Tuple[Unpack[TParam]]]:
    raise NotImplementedError

  def load_all(self) -> None:
    for i in self.get_all():
      self.load(*i)

  def reload(self) -> None:
    if self.reloadable == "eager":
      for key in self.cache:
        self.load(*key)
    elif self.reloadable == "lazy":
      for v in self.cache.values():
        v.need_reload = True
    else:
      raise ValueError(f"{self} 不可重载")


class SharedConfig(BaseConfig[TModel]):
  base_dir: ClassVar = "configs"

  def __init__(self, name: str, model: Type[TModel], reloadable: Reloadable = "lazy") -> None:
    super().__init__(model, reloadable)
    self.name = name

  def get_file(self) -> str:
    return f"{self.base_dir}/{self.name}.yaml"

  def get_all(self) -> Iterable[Tuple[()]]:
    yield ()


class SharedState(SharedConfig[TModel]):
  category = "状态"
  base_dir = "states"


class GroupConfig(BaseConfig[TModel, int]):
  base_dir: ClassVar = "configs"

  def __init__(self, name: str, model: Type[TModel], reloadable: Reloadable = "lazy") -> None:
    super().__init__(model, reloadable)
    self.name = name

  def get_file(self, group: int) -> str:
    file = f"{self.base_dir}/{self.name}/{group}.yaml"
    default_file = f"{self.base_dir}/{self.name}/default.yaml"
    if not os.path.exists(file) and os.path.exists(default_file):
      shutil.copy(default_file, file)
    return file

  def get_all(self) -> Iterable[Tuple[int]]:
    from . import context
    for i in context.CONFIG().groups:
      yield (i,)


class GroupState(GroupConfig[TModel]):
  category = "状态"
  base_dir = "states"
