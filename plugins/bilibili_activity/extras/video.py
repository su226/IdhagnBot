from typing import Callable

from PIL import ImageOps

from util import imutil, textutil
from util.api_common.bilibili_activity import ExtraVideo
from util.images.card import Card, CardTab

from ..common import fetch_image


async def format(extra: ExtraVideo) -> Callable[[Card], None]:
  cover = await fetch_image(extra.cover)

  def appender(card: Card) -> None:
    desc = f"{extra.duration} {extra.desc}"
    content = (
      f"{textutil.escape(extra.title)}\n"
      f"<span color='#888888'>{textutil.escape(desc)}</span>"
    )
    nonlocal cover
    cover = ImageOps.contain(cover, (160, 100), imutil.scale_resample())
    card.add(CardTab(content, "视频", cover))
  return appender
