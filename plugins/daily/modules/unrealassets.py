import os
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import unreal_free

from . import DailyCache, Module


class State(BaseModel):
  prev_assets: List[unreal_free.Asset] = Field(default_factory=list)
  assets: List[unreal_free.Asset] = Field(default_factory=list)


class UnrealAssetsCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("unrealassets.json")
    self.image_path = os.path.splitext(self.path)[0] + ".jpg"

  async def update(self) -> None:
    assets = await unreal_free.free_assets()
    if os.path.exists(self.path):
      model = State.parse_file(self.path)
    else:
      model = State()
    model.prev_assets = model.assets
    model.assets = assets
    json = model.json()
    with open(self.path, "w") as f:
      f.write(json)
    self.write_date()


cache = UnrealAssetsCache()


class UnrealAssetsModule(Module):
  def __init__(self, force: bool) -> None:
    self.force = force

  async def format(self) -> List[Message]:
    await cache.ensure()
    model = State.parse_file(cache.path)
    if self.force:
      assets = model.assets
    else:
      prev_slugs = set(game.slug for game in model.prev_assets)
      assets = [game for game in model.assets if game.slug not in prev_slugs]
    if not assets:
      return []
    message = Message(MessageSegment.text("今天可以喜加一："))
    for asset in assets:
      wrap = "\n" if message else ""
      message.extend([
        MessageSegment.text(
          f"{wrap}{asset.category}资产 {asset.title} 原价 {asset.price} 现在免费，"
          f"共 {asset.ratingCount} 条评价，平均 {asset.ratingScore}⭐\n"
          f"{unreal_free.URL_BASE}{asset.slug}\n"
        ),
        MessageSegment.image(asset.image)
      ])
    return [message]
