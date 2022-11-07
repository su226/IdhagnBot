import os
from datetime import datetime, timezone

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel, Field

from util.api_common import epicgames

from . import DailyCache, Module


class State(BaseModel):
  prev_games: list[epicgames.Game] = Field(default_factory=list)
  games: list[epicgames.Game] = Field(default_factory=list)


class EpicGamesCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("epicgames.json")
    self.image_path = os.path.splitext(self.path)[0] + ".jpg"

  async def update(self) -> None:
    games = await epicgames.free_games()
    now_date = datetime.now(timezone.utc)
    games = sorted(
      (x for x in games if now_date > x.start_date), key=lambda x: (x.end_date, x.slug)
    )
    if os.path.exists(self.path):
      model = State.parse_file(self.path)
    else:
      model = State()
    model.prev_games = model.games
    model.games = games
    json = model.json()
    with open(self.path, "w") as f:
      f.write(json)
    self.write_date()


cache = EpicGamesCache()


class EpicGamesModule(Module):
  def __init__(self, force: bool) -> None:
    self.force = force

  async def format(self) -> list[Message]:
    await cache.ensure()
    model = State.parse_file(cache.path)
    if not self.force and model.prev_games == model.games:
      return []
    message = Message(MessageSegment.text("今天可以喜加一："))
    for game in model.games:
      end_str = game.end_date.astimezone().strftime("%Y-%m-%d %H:%M")
      text = f"\n{game.title}，截止到 {end_str}\n{epicgames.URL_BASE}{game.slug}\n"
      message.extend([
        MessageSegment.text(text),
        MessageSegment.image(game.image)
      ])
    return [message]
