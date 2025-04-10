from datetime import datetime, timezone
from typing import Iterable, List, Optional
from dataclasses import dataclass

from pydantic import BaseModel

from util import misc

class ApiDiscountSetting(BaseModel):
  discountType: str
  discountPercentage: int


class ApiPromotionOffer(BaseModel):
  startDate: Optional[str]
  endDate: Optional[str]
  discountSetting: ApiDiscountSetting


class ApiPromotionOffers(BaseModel):
  promotionalOffers: list[ApiPromotionOffer]


class ApiPromotions(BaseModel):
  promotionalOffers: list[ApiPromotionOffers]
  upcomingPromotionalOffers: list[ApiPromotionOffers]


class ApiKeyImage(BaseModel):
  type: str
  url: str


class ApiMapping(BaseModel):
  pageType: str
  pageSlug: str


class ApiCatalogNs(BaseModel):
  mappings: Optional[list[ApiMapping]]


class ApiElement(BaseModel):
  title: str
  productSlug: Optional[str]
  urlSlug: str
  promotions: Optional[ApiPromotions]
  keyImages: list[ApiKeyImage]
  catalogNs: ApiCatalogNs
  offerMappings: Optional[list[ApiMapping]]


class ApiSearchStore(BaseModel):
  elements: list[ApiElement]


class ApiCatalog(BaseModel):
  searchStore: ApiSearchStore


class ApiData(BaseModel):
  Catalog: ApiCatalog


class ApiResult(BaseModel):
  data: ApiData


@dataclass
class Game:
  start_date: datetime
  end_date: datetime
  name: str
  image: str
  slug: str


__all__ = ["Game", "URL_BASE", "get_freebies"]
API = (
  "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
  "?locale=zh-CN&country=CN&allowCountries=CN"
)
URL_BASE = "https://www.epicgames.com/store/zh-CN/p/"
DISCOUNT_FREE = ApiDiscountSetting(discountType="PERCENTAGE", discountPercentage=0)


def iter_promotions(promotions: Optional[ApiPromotions]) -> Iterable[ApiPromotionOffer]:
  if not promotions:
    return
  for i in promotions.promotionalOffers:
    yield from i.promotionalOffers
  for i in promotions.upcomingPromotionalOffers:
    yield from i.promotionalOffers


def get_slug(game: ApiElement) -> str:
  for i in game.offerMappings or []:
    if i.pageType in ("productHome", "offer"):
      return i.pageSlug
  slug = game.productSlug
  if slug and slug != "[]":
    return slug.removesuffix("/home")
  return ""


def get_image(game: ApiElement) -> str:
  for i in game.keyImages:
    if i.type in ("DieselStoreFrontWide", "OfferImageWide"):
      return i.url
  return ""


async def get_freebies() -> List[Game]:
  http = misc.http()
  async with http.get(API) as response:
    data = ApiResult.model_validate(await response.json())
  games = data.data.Catalog.searchStore.elements
  result: List[Game] = []
  now_date = datetime.now(timezone.utc)
  for game in games:
    for i in iter_promotions(game.promotions):
      # Python不支持Z结束，须替换成+00:00
      if i.startDate is None or i.endDate is None:
        continue
      start_date = datetime.fromisoformat(i.startDate.replace("Z", "+00:00"))
      end_date = datetime.fromisoformat(i.endDate.replace("Z", "+00:00"))
      if i.discountSetting == DISCOUNT_FREE and start_date < end_date and now_date < end_date:
        result.append(Game(
          start_date=start_date,
          end_date=end_date,
          name=game.title,
          image=get_image(game),
          slug=get_slug(game),
        ))
        break
  return result
