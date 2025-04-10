import os
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import steam_freebies as api

from . import DailyCache, Module


class State(BaseModel):
  prev_games: List[api.Game] = Field(default_factory=list)
  games: List[api.Game] = Field(default_factory=list)


class SteamFreebiesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("steam_freebies.json")

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


cache = SteamFreebiesCache()


class SteamFreebiesModule(Module):
  def __init__(self, force: bool) -> None:
    self.force = force

  async def format(self) -> List[Message]:
    await cache.ensure()
    with open(cache.path) as f:
      model = State.model_validate_json(f.read())
    if self.force:
      games = model.games
    else:
      prev_appids = {game.appid for game in model.prev_games}
      games = [game for game in model.games if game.appid not in prev_appids]
    if not games:
      return []
    message = Message(MessageSegment.text("Steam 今天可以喜加一："))
    for game in games:
      wrap = "\n" if message else ""
      message.extend([
        MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.appid}\n"),
        MessageSegment.image(game.image),
      ])
    return [message]
