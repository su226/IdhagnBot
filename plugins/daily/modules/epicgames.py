import os
from datetime import datetime, timezone
from typing import List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import epic_free

from . import DailyCache, Module


class State(BaseModel):
  prev_games: List[epic_free.Game] = Field(default_factory=list)
  games: List[epic_free.Game] = Field(default_factory=list)


class EpicGamesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("epicgames.json")
    self.image_path = os.path.splitext(self.path)[0] + ".jpg"

  async def update(self) -> None:
    games = await epic_free.free_games()
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


cache = EpicGamesCache()


class EpicGamesModule(Module):
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
    message = Message(MessageSegment.text("今天可以喜加一："))
    for game in games:
      end_str = game.end_date.astimezone().strftime("%Y-%m-%d %H:%M")
      text = f"\n{game.title}，截止到 {end_str}\n{epic_free.URL_BASE}{game.slug}\n"
      message.extend([
        MessageSegment.text(text),
        MessageSegment.image(game.image),
      ])
    return [message]
