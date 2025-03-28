import os
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import fab_free

from . import DailyCache, Module


class State(BaseModel):
  prev_assets: List[fab_free.Asset] = Field(default_factory=list)
  assets: List[fab_free.Asset] = Field(default_factory=list)


class FabCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("fab.json")
    self.image_path = os.path.splitext(self.path)[0] + ".jpg"

  async def update(self) -> None:
    assets = await fab_free.free_assets()
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


cache = FabCache()


class FabModule(Module):
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
        MessageSegment.text(f"{wrap}{asset.title}\n{fab_free.URL_BASE}{asset.uid}\n"),
        MessageSegment.image(asset.image),
      ])
    return [message]
