import os
from datetime import datetime, timezone
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import epicgames_freebies as api

from . import DailyCache, Module


class State(BaseModel):
  prev_games: List[api.Game] = Field(default_factory=list)
  games: List[api.Game] = Field(default_factory=list)


class EpicGamesFreebiesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("epicgames_freebies.json")

  async def update(self) -> None:
    games = await api.get_freebies()
    now_date = datetime.now(timezone.utc)
    games = sorted(
      (x for x in games if now_date > x.start_date), key=lambda x: (x.end_date, x.slug),
    )
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


cache = EpicGamesFreebiesCache()


class EpicGamesFreebiesModule(Module):
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
    message = Message(MessageSegment.text("Epic Games 今天可以喜加一："))
    for game in games:
      end_str = game.end_date.astimezone().strftime("%Y-%m-%d %H:%M")
      text = f"\n{game.name}，截止到 {end_str}\n{api.URL_BASE}{game.slug}\n"
      message.extend([
        MessageSegment.text(text),
        MessageSegment.image(game.image),
      ])
    return [message]
