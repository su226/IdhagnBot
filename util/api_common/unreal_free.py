from dataclasses import dataclass
from typing import List, Literal, TypedDict
from typing_extensions import NotRequired

from pydantic import TypeAdapter

from util import misc

API = "https://www.unrealengine.com/marketplace/api/assets?lang=zh-CN&tag[]=4910"
HEADERS = {"Accept-Language": "zh-CN", "User-Agent": misc.BROWSER_UA, "Priority": "u=1"}
URL_BASE = "https://www.unrealengine.com/marketplace/zh-CN/product/"


class ResCategory(TypedDict):
  name: str


class ResRating(TypedDict):
  averageRating: float
  total: int


class ResElement(TypedDict):
  title: str
  price: str
  categories: List[ResCategory]
  urlSlug: str
  featured: str
  rating: NotRequired[ResRating]


class ResData(TypedDict):
  elements: List[ResElement]


class ResRoot(TypedDict):
  status: Literal["OK"]
  data: ResData


@dataclass
class Asset:
  title: str
  image: str
  slug: str
  category: str
  price: str
  ratingScore: float
  ratingCount: int


async def free_assets() -> List[Asset]:
  http = misc.http()
  async with http.get(API, headers=HEADERS) as response:
    data = TypeAdapter(ResRoot).validate_python(await response.json())
  assets: List[Asset] = []
  for asset in data["data"]["elements"]:
    rating = asset.get("rating")
    assets.append(Asset(
      asset["title"],
      asset["featured"],
      asset["urlSlug"],
      asset["categories"][0]["name"],
      asset["price"],
      rating["averageRating"] if rating else 0,
      rating["total"] if rating else 0,
    ))
  return assets
