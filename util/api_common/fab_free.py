from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from util import misc

API = "https://www.fab.com/i/layouts/homepage"
HEADERS = {"Accept-Language": "zh-CN", "User-Agent": misc.BROWSER_UA, "Priority": "u=0, i"}
URL_BASE = "https://www.fab.com/zh-cn/listings/"


class ApiThumbnail(BaseModel):
  mediaUrl: str


class ApiListing(BaseModel):
  title: str
  thumbnails: list[ApiThumbnail]
  uid: str


class ApiTile(BaseModel):
  listing: Optional[ApiListing]


class ApiBlade(BaseModel):
  tiles: list[ApiTile]
  title: str


class ApiResult(BaseModel):
  blades: list[ApiBlade]


@dataclass
class Asset:
  uid: str
  title: str
  image: str


async def free_assets() -> list[Asset]:
  async with misc.http().get(API, headers=HEADERS) as response:
    data = ApiResult.model_validate(await response.json())
  for blade in data.blades:
    if blade.title.startswith("限时免费"):
      return [
        Asset(
          tile.listing.uid,
          tile.listing.title,
          tile.listing.thumbnails[0].mediaUrl,
        ) for tile in blade.tiles if tile.listing
      ]
  return []

