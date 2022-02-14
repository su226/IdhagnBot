from typing import Iterable
from aiohttp import ClientSession
from datetime import datetime, timedelta, timezone
from nonebot.adapters.onebot.v11 import Message
import nonebot

API = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN&allowCountries=CN"
FREE = {"discountType": "PERCENTAGE", "discountPercentage": 0}
ZERO = timedelta()

def iter_promotions(promotions: list[dict]) -> Iterable[dict]:
  if promotions is None:
    return
  for i in promotions["promotionalOffers"]:
    yield from i["promotionalOffers"]
  for i in promotions["upcomingPromotionalOffers"]:
    yield from i["promotionalOffers"]

def iter_free_games(games: list[dict]) -> Iterable[str]:
  now_date = datetime.now(timezone.utc)
  for game in games:
    title = game["title"]
    url = f"https://www.epicgames.com/store/zh-CN/p/{game['urlSlug']}"
    image = ""
    for i in game["keyImages"]:
      if i["type"] == "DieselStoreFrontWide":
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

epicfree = nonebot.on_command("epicfree", aliases={"epic", "喜加一"})
epicfree.__cmd__ = ["epicfree", "epic", "喜加一"]
epicfree.__brief__ = "看看E宝又在送什么"
epicfree.__doc__ = '''\
/epicfree - 查看现在的免费游戏
你送游戏你是我宝，你卖游戏翻脸不认（雾）'''
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
