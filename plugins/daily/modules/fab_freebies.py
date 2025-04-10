import os
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import fab_freebies as api

from . import DailyCache, Module


class State(BaseModel):
  prev_assets: List[api.Asset] = Field(default_factory=list)
  assets: List[api.Asset] = Field(default_factory=list)


class FabFreebiesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("fab_freebies.json")

  async def update(self) -> None:
    assets = await api.get_freebies()
    if os.path.exists(self.path):
      with open(self.path) as f:
        model = State.model_validate_json(f.read())
    else:
      model = State()
    model.prev_assets = model.assets
    model.assets = assets
    with open(self.path, "w") as f:
      f.write(model.model_dump_json())
    self.write_date()


cache = FabFreebiesCache()


class FabFreebiesModule(Module):
  def __init__(self, force: bool) -> None:
    self.force = force

  async def format(self) -> List[Message]:
    await cache.ensure()
    with open(cache.path) as f:
      model = State.model_validate_json(f.read())
    if self.force:
      assets = model.assets
    else:
      prev_uids = {asset.uid for asset in model.prev_assets}
      assets = [asset for asset in model.assets if asset.uid not in prev_uids]
    if not assets:
      return []
    message = Message(MessageSegment.text("Fab 今天可以喜加一："))
    for asset in assets:
      wrap = "\n" if message else ""
      message.extend([
        MessageSegment.text(f"{wrap}{asset.name}\n{api.URL_BASE}{asset.uid}\n"),
        MessageSegment.image(asset.image),
      ])
    return [message]
