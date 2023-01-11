from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardText

from ..common import check_ignore, fetch_image

ActivityText = bilibili_activity.Activity[bilibili_activity.ContentText]


async def get_appender(activity: ActivityText) -> Callable[[Card], None]:
  avatar = await fetch_image(activity.avatar)

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardText(activity.content.text, 32, 6))
    card.add(block)

  return appender


async def format(activity: ActivityText) -> Message:
  check_ignore(False, activity.content.text)
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了动态\n"
      + imutil.to_segment(im)
      + f"\nhttps://t.bilibili.com/{activity.id}"
    )

  return await misc.to_thread(make)
