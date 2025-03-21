from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TypedDict

from pydantic import TypeAdapter
from typing_extensions import NotRequired

from util import misc

__all__ = ["free_games"]
API = (
  "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home"
  "?count=10&country=CN&locale=zh-CN&platform=android&start=0&store=EGS"
)


class ApiMediaItem(TypedDict):
  imageSrc: str


class ApiMedia(TypedDict):
  card16x9: ApiMediaItem


class ApiDiscount(TypedDict):
  discountAmountDisplay: str
  discountEndDate: str


class ApiPurchase(TypedDict):
  purchaseStateEffectiveDate: str
  discount: NotRequired[ApiDiscount]


class ApiContent(TypedDict):
  title: str
  media: ApiMedia
  purchase: list[ApiPurchase]


class ApiOffer(TypedDict):
  content: ApiContent


class ApiData(TypedDict):
  offers: list[ApiOffer]
  type: str


class ApiRoot(TypedDict):
  data: list[ApiData]


@dataclass
class Game:
  start_date: datetime
  end_date: datetime
  title: str
  image: str


async def free_games() -> list[Game]:
  http = misc.http()
  async with http.get(API, headers={"User-Agent": misc.BROWSER_UA}) as Apiponse:
    data = TypeAdapter(ApiRoot).validate_python(await Apiponse.json())
  for topic in data["data"]:
    if topic["type"] == "freeGame":
      offers = topic["offers"]
      break
  else:
    return []
  games: list[Game] = []
  now_date = datetime.now(timezone.utc)
  for offer in offers:
    for purchase in offer["content"]["purchase"]:
      if "discount" in purchase and purchase["discount"]["discountAmountDisplay"] == "-100%":
        start_date = purchase["purchaseStateEffectiveDate"]
        end_date = purchase["discount"]["discountEndDate"]
        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        if start_date < end_date and now_date < end_date:
          games.append(Game(
            start_date=start_date,
            end_date=end_date,
            title=offer["content"]["title"],
            image=offer["content"]["media"]["card16x9"]["imageSrc"],
          ))
          break
  return games
