import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image, ImageOps

from util import imutil, misc
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import IMAGE_GAP, fetch_image, fetch_images

ActivityArticle = bilibili_activity.Activity[bilibili_activity.ContentArticle]


async def get_appender(activity: ActivityArticle) -> Callable[[Card], None]:
  avatar, covers = await asyncio.gather(
    fetch_image(activity.avatar), fetch_images(*activity.content.covers)
  )

  def appender(card: Card) -> None:
    nonlocal covers
    if len(covers) == 1:
      cover = covers[0]
    else:
      gaps = len(covers) - 1
      size = 640 - gaps * IMAGE_GAP
      covers = [ImageOps.fit(cover, (size, size), imutil.resample()) for cover in covers]
      cover = Image.new("RGB", (640, size), (255, 255, 255))
      for i, v in enumerate(covers):
        cover.paste(v, (i * (size + IMAGE_GAP), 0))
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardText(activity.content.title, 40, 2))
    card.add(block)
    card.add(CardCover(cover, False))
    block = Card()
    block.add(CardText(activity.content.desc, 32, 3))
    card.add(block)

  return appender


async def format(activity: ActivityArticle) -> Message:
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了专栏\n"
      + imutil.to_segment(im)
      + f"\nhttps://www.bilibili.com/read/cv{activity.content.id}"
    )

  return await misc.to_thread(make)
