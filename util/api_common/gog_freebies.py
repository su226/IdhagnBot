from dataclasses import dataclass

from pydantic import BaseModel

from util import misc

__all__ = ["Game", "URL_BASE", "get_freebies"]
API = (
  "https://catalog.gog.com/v1/catalog?limit=48&price=between%3A0%2C0&order=desc%3Atrending"
  "&discounted=eq%3Atrue&productType=in%3Agame%2Cpack%2Cdlc%2Cextras&page=1&countryCode=CN"
  "&locale=zh-Hans&currencyCode=CNY"
)
URL_BASE = "https://www.gog.com/zh/game/"


class ApiProduct(BaseModel):
  slug: str
  title: str
  coverHorizontal: str


class ApiResult(BaseModel):
  products: list[ApiProduct]


@dataclass
class Game:
  slug: str
  name: str
  image: str


async def get_freebies() -> list[Game]:
  http = misc.http()
  async with http.get(API) as Apiponse:
    data = ApiResult.model_validate(await Apiponse.json())
  games: list[Game] = []
  for product in data.products:
    games.append(Game(
      slug=product.slug,
      name=product.title,
      image=product.coverHorizontal,
    ))
  return games
