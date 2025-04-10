from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from util import misc

__all__ = ["Game", "get_freebies"]
API = (
  "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home"
  "?count=10&country=CN&locale=zh-CN&platform=android&start=0&store=EGS"
)


class ApiMediaItem(BaseModel):
  imageSrc: str


class ApiMedia(BaseModel):
  card16x9: ApiMediaItem


class ApiDiscount(BaseModel):
  discountAmountDisplay: str
  discountEndDate: str


class ApiPurchase(BaseModel):
  purchaseStateEffectiveDate: str
  discount: Optional[ApiDiscount] = None


class ApiContent(BaseModel):
  title: str
  media: ApiMedia
  purchase: list[ApiPurchase]


class ApiOffer(BaseModel):
  content: ApiContent


class ApiData(BaseModel):
  offers: list[ApiOffer]
  type: str


class ApiResult(BaseModel):
  data: list[ApiData]


@dataclass
class Game:
  start_date: datetime
  end_date: datetime
  name: str
  image: str


async def get_freebies() -> list[Game]:
  http = misc.http()
  async with http.get(API, headers={"User-Agent": misc.BROWSER_UA}) as Apiponse:
    data = ApiResult.model_validate(await Apiponse.json())
  for topic in data.data:
    if topic.type == "freeGame":
      offers = topic.offers
      break
  else:
    return []
  games: list[Game] = []
  now_date = datetime.now(timezone.utc)
  for offer in offers:
    for purchase in offer.content.purchase:
      if purchase.discount and purchase.discount.discountAmountDisplay == "-100%":
        start_date = purchase.purchaseStateEffectiveDate
        end_date = purchase.discount.discountEndDate
        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        if start_date < end_date and now_date < end_date:
          games.append(Game(
            start_date=start_date,
            end_date=end_date,
            name=offer.content.title,
            image=offer.content.media.card16x9.imageSrc,
          ))
          break
  return games
