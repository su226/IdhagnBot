# ADDITIONAL_TYPE_PGC
# ADDITIONAL_TYPE_GOODS
# ADDITIONAL_TYPE_VOTE    # 投票
# ADDITIONAL_TYPE_COMMON
# ADDITIONAL_TYPE_MATCH
# ADDITIONAL_TYPE_UP_RCMD
# ADDITIONAL_TYPE_UGC     # 视频
# ADDITIONAL_TYPE_RESERVE # 直播预约

from typing import Any, Awaitable, Callable, List, Tuple, Type, TypeVar

from util.api_common.bilibili_activity import ExtraReserve, ExtraVideo, ExtraVote
from util.images.card import Card, CardMargin, CardTab

from . import reserve, video, vote

TExtra = TypeVar("TExtra")
Formatter = Tuple[Type[TExtra], Callable[[TExtra], Awaitable[Callable[[Card], None]]]]
FORMATTERS: List[Formatter[Any]] = [
  (ExtraVote, vote.format),
  (ExtraVideo, video.format),
  (ExtraReserve, reserve.format),
]


def format_noop(card: Card, block: bool = False) -> None:
  pass


def format_unknown(card: Card) -> None:
  card.add(CardTab("IdhagnBot 暂不支持解析此内容", "额外内容"))


async def format(extra: object) -> Callable[[Card, bool], None]:
  if extra is None:
    return format_noop
  for type, get_appender in FORMATTERS:
    if isinstance(extra, type):
      appender = await get_appender(extra)
      break
  else:
    appender = format_unknown

  def do_format(card: Card, block: bool = False) -> None:
    if block:
      content = Card()
      appender(content)
      card.add(content)
    else:
      card.add(CardMargin())
      appender(card)

  return do_format
