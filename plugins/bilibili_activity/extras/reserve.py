from typing import Callable

from util import textutil
from util.api_common.bilibili_activity import ExtraReserve
from util.images.card import Card, CardTab


async def format(extra: ExtraReserve) -> Callable[[Card], None]:
  def appender(card: Card) -> None:
    content = (
      f"{textutil.escape(extra.title)}\n"
      f"<span color='#888888'>{textutil.escape(extra.desc)} {extra.count}人已预约</span>"
    )
    card.add(CardTab(content, "预约"))
  return appender
