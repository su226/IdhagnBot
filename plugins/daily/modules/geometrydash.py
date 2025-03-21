import os
from typing import List, Optional

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from pydantic import BaseModel

from util import misc

from . import DailyCache, Module


# SERVER = "https://www.boomlings.com/database"  # noqa: ERA001
SERVER = "https://endless-services.zhazha120.cn/api/EndlessProxy/GeometryDash"


class Level(BaseModel):
  id: int
  name: str
  downloads: int
  likes: int
  length: int
  stars: int
  coins: int
  daily: int
  demon: int
  author: str
  demon_tier: Optional[float] = None
  has_image: bool = False

  @staticmethod
  def parse(data: str) -> "Level":
    level, _, _, author, *_ = data.split("#")
    data1 = dict(misc.chunked(level.split(":"), 2))
    return Level.model_validate({
      "id": data1["1"],
      "name": data1["2"],
      "downloads": data1["10"],
      "likes": data1["14"],
      "length": data1["15"],
      "stars": data1["18"],
      "coins": data1["37"],
      "daily": data1["41"],
      "demon": data1["43"],
      "author": author.split(":")[1],
    })

  def difficulty_name(self) -> str:
    if self.stars == 1:
      return "Auto"
    if self.stars == 2:
      return "Easy"
    if self.stars == 3:
      return "Normal"
    if self.stars in (4, 5):
      return "Hard"
    if self.stars in (6, 7):
      return "Harder"
    if self.stars in (8, 9):
      return "Insane"
    if self.stars == 10:
      if self.demon == 3:
        return "Easy Demon"
      if self.demon == 4:
        return "Medium Demon"
      if self.demon == 0:
        return "Hard Demon"
      if self.demon == 5:
        return "Insane Demon"
      if self.demon == 6:
        return "Extreme Demon"
    return "N/A"

  def length_name(self) -> str:
    if self.length == 0:
      return "Tiny"
    if self.length == 1:
      return "Short"
    if self.length == 2:
      return "Medium"
    if self.length == 3:
      return "Long"
    if self.length == 4:
      return "XL"
    return "Plat."
  
  def orbs(self) -> int:
    if self.stars == 2:
      return 50
    if self.stars == 3:
      return 75
    if self.stars == 4:
      return 125
    if self.stars == 5:
      return 175
    if self.stars == 6:
      return 225
    if self.stars == 7:
      return 275
    if self.stars == 8:
      return 350
    if self.stars == 9:
      return 425
    if self.stars == 10:
      return 500
    return 0

  def id_equals(self, other: Optional["Level"]) -> bool:
    if other:
      return other.id == self.id
    return False


class State(BaseModel):
  prev_level: Optional[Level] = None
  level: Optional[Level] = None


class GeometryDashCache(DailyCache):
  def __init__(self, name: str, id: int) -> None:
    super().__init__(f"geometrydash{name}.json")
    self.image_path = os.path.splitext(self.path)[0] + ".png"
    self.id = id

  async def update(self) -> None:
    async with misc.http().post(
      f"{SERVER}/downloadGJLevel22.php", skip_auto_headers=["User-Agent"],
      data={"secret": "Wmfd2893gb7", "levelID": self.id},
    ) as response:
      level = Level.parse(await response.text())
    async with misc.http().get(
      f"https://raw.githubusercontent.com/cdc-sys/level-thumbnails/main/thumbs/{level.id}.png",
    ) as response:
      if response.status == 200:
        with open(self.image_path, "wb") as f:
          f.write(await response.read())
          level.has_image = True
    if level.stars == 10:
      async with misc.http().get(f"https://gdladder.com/api/level/{level.id}") as response:
        data = await response.json()
        level.demon_tier = data.get("Rating")
    if os.path.exists(self.path):
      with open(self.path) as f:
        model = State.model_validate_json(f.read())
    else:
      model = State()
    model.prev_level = model.level
    model.level = level
    with open(self.path, "w") as f:
      f.write(model.model_dump_json())
    self.write_date()


daily_cache = GeometryDashCache("daily", -1)
weekly_cache = GeometryDashCache("weekly", -2)
event_cache = GeometryDashCache("event", -3)


class GeometryDashModule(Module):
  def __init__(self, cache: GeometryDashCache, force: bool) -> None:
    self.force = force
    self.cache = cache

  async def format(self) -> List[Message]:
    await self.cache.ensure()
    with open(self.cache.path) as f:
      model = State.model_validate_json(f.read())
    level = model.level
    if not level:
      return []
    if not self.force and level.id_equals(model.prev_level):
      return []
    demon_tier = f" T{round(level.demon_tier)}" if level.demon_tier is not None else ""
    coins = f" {'🪙' * level.coins}" if level.coins else ""
    if level.daily >= 200000:
      description = "event level"
      daily_id = f"Event #{level.daily - 200000}"
    elif level.daily >= 100000:
      description = "weekly demon"
      daily_id = f"Weekly #{level.daily - 100000}"
    else:
      description = "daily level"
      daily_id = f"Daily #{level.daily}"
    message = Message(MessageSegment.text(f'''\
New {description}: "{level.name}" by {level.author}
Level #{level.id} {daily_id}
{level.difficulty_name()}{demon_tier} {level.stars}⭐{coins}
🕔{level.length_name()} ⬇️{level.downloads} 👍{level.likes} 🔮{level.orbs()}'''))
    if level.has_image:
      message += misc.local("image", self.cache.image_path)
    return [message]
