import asyncio
import math
from typing import Callable

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image, ImageOps

from util import imutil, misc
from util.api_common.bilibili_activity import ActivityImage
from util.api_common.bilibili_activity.card import CardRichText, fetch_emotions
from util.images.card import Card, CardAuthor, CardCover

from .. import extras
from ..common import IMAGE_GAP, check_ignore, fetch_image, fetch_images


async def get_appender(activity: ActivityImage[object]) -> Callable[[Card], None]:
  image_infos = (
    activity.content.images[:9] if len(activity.content.images) > 9 else activity.content.images
  )
  avatar, images, emotions, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_images(*[image.src for image in image_infos]),
    fetch_emotions(activity.content.richtext),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    nonlocal images
    if len(images) == 1:
      cover = ImageOps.fit(images[0], (640, 400), imutil.resample())
    else:
      columns = 2 if len(images) in {2, 4} else 3
      rows = math.ceil(len(images) / columns)
      size = (640 - (columns - 1) * IMAGE_GAP) // columns
      height = size * rows + max(rows - 1, 0) * IMAGE_GAP
      images = [ImageOps.fit(image, (size, size), imutil.resample()) for image in images]
      cover = Image.new("RGB", (640, height), (255, 255, 255))
      for i, v in enumerate(images):
        y, x = divmod(i, columns)
        x = int(x / (columns - 1) * (640 - size))
        y = y * (size + IMAGE_GAP)
        cover.paste(v, (x, y))
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardRichText(activity.content.richtext, emotions, 32, 3, activity.topic))
    card.add(block)
    card.add(CardCover(cover, False))
    append_extra(card, True)

  return appender


async def format(activity: ActivityImage[object], can_ignore: bool) -> Message:
  if can_ignore:
    check_ignore(activity.content.text)
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return Message([
      MessageSegment.text(f"{activity.name} 发布了动态\n"),
      imutil.to_segment(im),
      MessageSegment.text(f"\nhttps://t.bilibili.com/{activity.id}"),
    ])

  return await misc.to_thread(make)
