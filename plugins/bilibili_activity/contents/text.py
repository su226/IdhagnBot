import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common.bilibili_activity import ActivityText
from util.api_common.bilibili_activity.card import CardRichText, fetch_emotions
from util.images.card import Card, CardAuthor

from .. import extras
from ..common import check_ignore, fetch_image


async def get_appender(activity: ActivityText[object]) -> Callable[[Card], None]:
  avatar, emotions, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_emotions(activity.content.richtext),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    lines = 3 if activity.extra else 6
    block.add(CardRichText(activity.content.richtext, emotions, 32, lines, activity.topic))
    append_extra(block, False)
    card.add(block)

  return appender


async def format(activity: ActivityText[object], can_ignore: bool) -> Message:
  if can_ignore:
    check_ignore(False, activity.content.text)
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return Message([
      f"{activity.name} 发布了动态\n",
      imutil.to_segment(im),
      f"\nhttps://t.bilibili.com/{activity.id}"
    ])

  return await misc.to_thread(make)
