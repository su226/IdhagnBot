import os
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import gog_freebies as api

from . import DailyCache, Module


class State(BaseModel):
  prev_games: List[api.Game] = Field(default_factory=list)
  games: List[api.Game] = Field(default_factory=list)


class GogFreebiesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("gog_freebies.json")

  async def update(self) -> None:
    games = await api.get_freebies()
    if os.path.exists(self.path):
      with open(self.path) as f:
        model = State.model_validate_json(f.read())
    else:
      model = State()
    model.prev_games = model.games
    model.games = games
    with open(self.path, "w") as f:
      f.write(model.model_dump_json())
    self.write_date()


cache = GogFreebiesCache()


class GogFreebiesModule(Module):
  def __init__(self, force: bool) -> None:
    self.force = force

  async def format(self) -> List[Message]:
    await cache.ensure()
    with open(cache.path) as f:
      model = State.model_validate_json(f.read())
    if self.force:
      games = model.games
    else:
      prev_slugs = {game.slug for game in model.prev_games}
      games = [game for game in model.games if game.slug not in prev_slugs]
    if not games:
      return []
    message = Message(MessageSegment.text("GOG 今天可以喜加一："))
    for game in games:
      wrap = "\n" if message else ""
      message.extend([
        MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.slug}\n"),
        MessageSegment.image(game.image),
      ])
    return [message]
