import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common.bilibili_activity import ActivityAudio
from util.api_common.bilibili_activity.card import CardTopic
from util.images.card import Card, CardAuthor, CardCover, CardText

from .. import extras
from ..common import fetch_image


async def get_appender(activity: ActivityAudio[object]) -> Callable[[Card], None]:
  avatar, cover, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.title, 40, 2))
    block.add(CardText(activity.content.label, 32, 1))
    card.add(block)
    card.add(CardCover(cover))
    if activity.content.desc and activity.content.desc != "-":
      block = Card()
      block.add(CardText(activity.content.desc, 32, 3))
      append_extra(block, False)
      card.add(block)
    else:
      append_extra(card, True)

  return appender


async def format(activity: ActivityAudio[object]) -> Message:
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了音频\n"
      + imutil.to_segment(im)
      + f"\nhttps://www.bilibili.com/audio/au{activity.content.id}"
    )

  return await misc.to_thread(make)
