import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import nonebot
import yaml
from loguru import logger
from pydantic import BaseModel, Field

from . import configs


class Config(BaseModel):
  blacklist: Set[str] = Field(default_factory=set)
  invert_blacklist: bool = False
  extra_plugins: Set[str] = Field(default_factory=set)
  extra_dirs: Set[str] = Field(default_factory=lambda: {"user_plugins"})


class Metadata(BaseModel):
  requirements: Dict[str, List[str]]
  groups: Dict[str, str]


@dataclass
class Missing:
  name: str
  requires: List[str]
  groups: List[str]


CONFIG = configs.SharedConfig("plugins", Config, False)
ROOT_DIR = Path(__file__).resolve().parents[1]
MODULES: Dict[str, bool] = {}
with open(ROOT_DIR / "plugins" / "metadata.yaml") as f:
  METADATA = Metadata.parse_obj(yaml.load(f, configs.SafeLoader))


def children(parent: str) -> Tuple[List[str], List[Missing]]:
  from . import misc
  config = CONFIG()
  path = ROOT_DIR / parent.replace(".", "/")
  availables: List[str] = []
  missings: List[Missing] = []
  for child in pkgutil.iter_modules([str(path)]):
    meta_name = misc.removeprefix(f"{parent}.{child.name}", "plugins.")
    if (
      child.name.startswith("_")
      or (meta_name in config.blacklist != config.invert_blacklist)
    ):
      continue
    requirements = METADATA.requirements.get(meta_name, None)
    if not requirements:
      availables.append(child.name)
      continue
    missing: List[str] = []
    for module in requirements:
      if module not in MODULES:
        try:
          importlib.import_module(module)
        except ImportError:
          MODULES[module] = False
        else:
          MODULES[module] = True
      if not MODULES[module]:
        missing.append(module)
    if missing:
      missings.append(Missing(
        child.name, missing, list({METADATA.groups[module] for module in missing})
      ))
    else:
      availables.append(child.name)
  return availables, missings


def load_children(parent: str) -> None:
  availables, missings = children(parent)
  for i in missings:
    logger.opt(depth=1).warning(
      f"子模块 {i.name} 因为缺失依赖 {'、'.join(i.requires)} 而不会被加载，"
      "你可以使用此命令来安装: pdm install"
      + "".join(f" -G {group}" for group in i.groups)
    )
  count = 0
  for i in availables:
    try:
      importlib.import_module(f"{parent}.{i}")
    except Exception:
      logger.opt(depth=1).exception(
        f"子模块 {i} 加载失败，这可能是 IdhagnBot 的问题，你可以尝试反馈。"
      )
    else:
      count += 1
  logger.opt(depth=1).success(f"加载了 {count} 个子模块")


def load_plugins():
  config = CONFIG()
  availables, missings = children("plugins")
  for i in missings:
    logger.warning(
      f"插件 {i.name} 因为缺失依赖 {'、'.join(i.requires)} 而不会被加载，"
      "你可以使用此命令来安装: pdm install"
      + "".join(f" -G {group}" for group in i.groups)
    )
  nonebot.load_all_plugins((f"plugins.{name}" for name in availables), ())
  nonebot.load_all_plugins(config.extra_plugins, config.extra_dirs)
