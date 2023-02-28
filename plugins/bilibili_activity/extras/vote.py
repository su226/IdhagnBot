from time import localtime, strftime
from typing import Callable

from util import textutil
from util.api_common.bilibili_activity import ExtraVote
from util.images.card import Card, CardTab


async def format(extra: ExtraVote) -> Callable[[Card], None]:
  def appender(card: Card) -> None:
    end_time = strftime("%m-%d %H:%M", localtime(extra.end))
    content = (
      f"{textutil.escape(extra.title)}\n"
      f"<span color='#888888'>{extra.count}人已投票 {end_time}截止</span>"
    )
    card.add(CardTab(content, "投票"))
  return appender
