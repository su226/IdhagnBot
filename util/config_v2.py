# 当我写下这段时，只有上帝和我明白我在做什么
# 现在只有上帝明白了

from typing import Any, Callable, ClassVar, Generic, Iterable, TypeVar
from typing_extensions import TypeVarTuple, Unpack
import os
import shutil

from loguru import logger
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
import yaml

from . import context

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
class BaseConfig(Generic[TModel, Unpack[TParam]]):
  category: ClassVar = "配置"
  all: ClassVar[list["BaseConfig"]] = []
  model: type[TModel]
  cache: dict[tuple[Unpack[TParam]], TModel]
  reloadable: bool
  handler: LoadHandler | None
  
  def __init__(self, model: type[TModel], reloadable: bool = True) -> None:
    self.model = model
    self.cache = {}
    self.reloadable = reloadable
    self.handler = None
    self.loaded = False
    self.all.append(self)

  def get_file(self, *args: Unpack[TParam]) -> str:
    raise NotImplementedError

  def __call__(self, *args: Unpack[TParam]) -> TModel:
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
      try:
        with open(file) as f:
          self.cache[args] = self.model.parse_obj(yaml.load(f, yaml.CSafeLoader))
      except Exception:
        logger.opt(exception=True).warning(f"无法读取{self.category}：{file}")
        self.cache[args] = self.model()
    else:
      logger.info(f"{self.category}文件不存在: {file}")
      self.cache[args] = self.model()
    if self.handler is not None:
      self.handler(old_config, self.cache[args], *args)

  def dump(self, *args: Unpack[TParam]) -> None:
    if args not in self.cache:
      return
    data = encode(self.cache[args].dict())
    file = self.get_file(*args)
    try:
      with open(file, "w") as f:
        yaml.dump(data, f, yaml.CSafeDumper, allow_unicode=True)
    except:
      logger.opt(exception=True).warning(f"无法记录{self.category}：{file}")

  def onload(self, immediate: bool = True) -> Callable[[LoadHandler], LoadHandler]:
    def decorator(handler: LoadHandler) -> LoadHandler:
      self.handler = handler
      if immediate:
        self.load_all()
      return handler
    return decorator

  def get_all(self) -> Iterable[tuple[Unpack[TParam]]]:
    raise NotImplementedError

  def load_all(self) -> None:
    for i in self.get_all():
      self.load(*i)

class SharedConfig(BaseConfig[TModel]):
  base_dir: ClassVar = "configs"

  def __init__(self, name: str, model: type[TModel], reloadable: bool = True) -> None:
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

  def __init__(self, name: str, model: type[TModel], reloadable: bool = True) -> None:
    super().__init__(model, reloadable)
    self.name = name

  def get_file(self, group: int) -> str:
    file = f"{self.base_dir}/{self.name}/{group}.yaml"
    default_file = f"{self.base_dir}/{self.name}/default.yaml"
    if not os.path.exists(file) and os.path.exists(default_file):
      shutil.copy(default_file, file)
    return file

  def get_all(self) -> Iterable[tuple[int]]:
    for i in context.CONFIG.groups:
      yield i,

class GroupState(GroupConfig[TModel]):
  category = "状态"
  base_dir = "states"
