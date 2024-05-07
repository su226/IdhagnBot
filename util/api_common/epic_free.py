from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from pydantic import BaseModel

from util import misc

API = (
  "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
  "?locale=zh-CN&country=CN&allowCountries=CN"
)
URL_BASE = "https://www.epicgames.com/store/zh-CN/p/"
FREE = {"discountType": "PERCENTAGE", "discountPercentage": 0}


class Game(BaseModel):
  start_date: datetime
  end_date: datetime
  title: str
  image: str
  slug: str


def promotions(promotions: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
  if not promotions:
    return
  for i in promotions["promotionalOffers"]:
    yield from i["promotionalOffers"]
  for i in promotions["upcomingPromotionalOffers"]:
    yield from i["promotionalOffers"]


def getslug(game: Dict[str, Any]) -> str:
  slug = game["productSlug"]
  if slug and slug != "[]":
    return slug.removesuffix("/home")
  for i in game["offerMappings"]:
    if i.get("pageType", "") == "productHome":
      return i["pageSlug"]
  return ""


def getimage(game: Dict[str, Any]) -> str:
  for i in game["keyImages"]:
    if i["type"] in ("DieselStoreFrontWide", "OfferImageWide"):
      return i["url"]
  return ""


async def free_games() -> List[Game]:
  http = misc.http()
  async with http.get(API) as response:
    data = await response.json()
  games = data["data"]["Catalog"]["searchStore"]["elements"]
  result: List[Game] = []
  now_date = datetime.now(timezone.utc)
  for game in games:
    for i in promotions(game.get("promotions", {})):
      # Python不支持Z结束，须替换成+00:00
      if i["startDate"] is None or i["endDate"] is None:
        continue
      start_date = datetime.fromisoformat(i["startDate"].replace("Z", "+00:00"))
      end_date = datetime.fromisoformat(i["endDate"].replace("Z", "+00:00"))
      if i["discountSetting"] == FREE and start_date < end_date and now_date < end_date:
        result.append(Game(
          start_date=start_date, end_date=end_date, title=game["title"], image=getimage(game),
          slug=getslug(game),
        ))
        break
  return result
