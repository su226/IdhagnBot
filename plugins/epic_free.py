from datetime import datetime, timedelta, timezone
from typing import Iterable

from aiohttp import ClientSession
from nonebot.adapters.onebot.v11 import Message

from util import command

API = (
  "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=zh-CN"
  "&country=CN&allowCountries=CN")
FREE = {"discountType": "PERCENTAGE", "discountPercentage": 0}
ZERO = timedelta()


def iter_promotions(promotions: dict) -> Iterable[dict]:
  if promotions is None:
    return
  for i in promotions["promotionalOffers"]:
    yield from i["promotionalOffers"]
  for i in promotions["upcomingPromotionalOffers"]:
    yield from i["promotionalOffers"]


def getslug(game: dict) -> str | None:
  slug = game['productSlug']
  if slug and slug != "[]":
    return slug.removesuffix("/home")
  for i in game["offerMappings"]:
    if i.get("pageType", None) == "productHome":
      return i["pageSlug"]
  return None


def iter_free_games(games: list[dict]) -> Iterable[str]:
  now_date = datetime.now(timezone.utc)
  for game in games:
    title = game["title"]
    slug = getslug(game)
    url = "链接未知" if not slug else f"https://www.epicgames.com/store/zh-CN/p/{slug}"
    image = ""
    for i in game["keyImages"]:
      if i["type"] in ("DieselStoreFrontWide", "OfferImageWide"):
        image = i["url"]
        break
    for i in iter_promotions(game.get("promotions", None)):
      # Python不支持Z结束，须替换成+00:00
      start_date = datetime.fromisoformat(i["startDate"].replace("Z", "+00:00"))
      start_date_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S")
      end_date = datetime.fromisoformat(i["endDate"].replace("Z", "+00:00"))
      end_date_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S")
      if i["discountSetting"] == FREE and end_date - start_date > ZERO:
        if start_date < now_date < end_date:
          yield f"[CQ:image,file={image}]{title} 目前免费，截止到 {end_date_str}\n{url}"
          break
        elif now_date < start_date:
          yield f"[CQ:image,file={image}]{title} 将在 {start_date_str} 免费，截止到 {end_date_str}\n{url}"
          break


epicfree = (
  command.CommandBuilder("epicfree", "epicfree", "epic", "喜加一")
  .brief("看看E宝又在送什么")
  .usage('''\
/epicfree - 查看现在的免费游戏
你送游戏你是我宝，你卖游戏翻脸不认（雾）''')
  .build())


@epicfree.handle()
async def handle_epicfree():
  async with ClientSession() as http:
    response = await http.get(API)
    data = await response.json()
  result = "\n".join(iter_free_games(data["data"]["Catalog"]["searchStore"]["elements"]))
  if not result:
    await epicfree.finish("似乎没有可白嫖的游戏")
  else:
    await epicfree.finish(Message(result))
