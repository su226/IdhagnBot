import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import fetch_image

ActivityVideo = bilibili_activity.Activity[bilibili_activity.ContentVideo]


async def get_appender(activity: ActivityVideo) -> Callable[[Card], None]:
  avatar, cover = await asyncio.gather(
    fetch_image(activity.avatar), fetch_image(activity.content.cover)
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    if activity.content.text:
      block.add(CardText(activity.content.text, 32, 3))
    block.add(CardText(activity.content.title, 40, 2))
    card.add(block)
    card.add(CardCover(cover))
    if activity.content.desc and activity.content.desc != "-":
      block = Card()
      block.add(CardText(activity.content.desc, 32, 3))
      card.add(block)

  return appender


async def format(activity: ActivityVideo) -> Message:
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了视频\n"
      + imutil.to_segment(im)
      + f"\nhttps://www.bilibili.com/video/{activity.content.bvid}"
    )

  return await misc.to_thread(make)
