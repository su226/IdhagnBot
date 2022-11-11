import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import fetch_image

ActivityAudio = bilibili_activity.Activity[bilibili_activity.ContentAudio]


async def get_appender(activity: ActivityAudio) -> Callable[[Card], None]:
  avatar, cover = await asyncio.gather(
    fetch_image(activity.avatar), fetch_image(activity.content.cover)
  )

  def appender(card: Card) -> None:
    card.add(CardAuthor(avatar, activity.name))
    card.add(CardText(activity.content.title, 40, 2))
    card.add(CardText(activity.content.label, 32, 1))
    card.add(CardCover(cover))
    if activity.content.desc and activity.content.desc != "-":
      card.add(CardText(activity.content.desc, 32, 3))

  return appender


async def format(activity: ActivityAudio) -> Message:
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card()
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了音频\n"
      + imutil.to_segment(im)
      + f"\nhttps://www.bilibili.com/audio/au{activity.content.id}"
    )

  return await asyncio.to_thread(make)
