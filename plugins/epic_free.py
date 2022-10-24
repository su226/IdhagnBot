from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command, util

API = (
  "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
  "?locale=zh-CN&country=CN&allowCountries=CN"
)
URL_BASE = "https://www.epicgames.com/store/zh-CN/p/"
FREE = {"discountType": "PERCENTAGE", "discountPercentage": 0}


@dataclass
class Game:
  start_date: datetime
  end_date: datetime
  title: str
  image: str
  slug: str


def promotions(promotions: dict) -> Iterable[dict]:
  if not promotions:
    return
  for i in promotions["promotionalOffers"]:
    yield from i["promotionalOffers"]
  for i in promotions["upcomingPromotionalOffers"]:
    yield from i["promotionalOffers"]


def getslug(game: dict) -> str:
  slug = game["productSlug"]
  if slug and slug != "[]":
    return slug.removesuffix("/home")
  for i in game["offerMappings"]:
    if i.get("pageType", "") == "productHome":
      return i["pageSlug"]
  return ""


def getimage(game: dict) -> str:
  for i in game["keyImages"]:
    if i["type"] in ("DieselStoreFrontWide", "OfferImageWide"):
      return i["url"]
  return ""


def free_games(games: list[dict]) -> Iterable[Game]:
  now_date = datetime.now(timezone.utc)
  for game in games:
    for i in promotions(game.get("promotions", {})):
      # Python不支持Z结束，须替换成+00:00
      start_date = datetime.fromisoformat(i["startDate"].replace("Z", "+00:00"))
      end_date = datetime.fromisoformat(i["endDate"].replace("Z", "+00:00"))
      if i["discountSetting"] == FREE and start_date < end_date and now_date < end_date:
        yield Game(start_date, end_date, game["title"], getimage(game), getslug(game))
        break


epicfree = command.CommandBuilder("epicfree", "epicfree", "epic", "e宝", "喜加一") \
  .brief("看看E宝又在送什么") \
  .usage('''\
/epicfree - 查看现在的免费游戏
你送游戏你是我宝，你卖游戏翻脸不认（雾）''') \
  .build()
@epicfree.handle()
async def handle_epicfree():
  http = util.http()
  async with http.get(API) as response:
    data = await response.json()
  games = list(free_games(data["data"]["Catalog"]["searchStore"]["elements"]))
  if not games:
    await epicfree.finish("似乎没有可白嫖的游戏")
  games.sort(key=lambda x: x.end_date)
  now_date = datetime.now(timezone.utc)
  message = Message()
  for game in games:
    end_str = game.end_date.astimezone().strftime("%Y-%m-%d %H:%M")
    if now_date > game.start_date:
      text = f"{game.title} 目前免费，截止到 {end_str}"
    else:
      start_str = game.start_date.astimezone().strftime("%Y-%m-%d %H:%M")
      text = f"{game.title} 将在 {start_str} 免费，截止到 {end_str}"
    if message:
      text = "\n" + text
    message.extend([
      MessageSegment.text(text + f"\n{URL_BASE}{game.slug}\n"),
      MessageSegment.image(game.image)
    ])
  await epicfree.finish(Message(message))
