import asyncio
import math
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image, ImageOps

from util import imutil, misc
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import IMAGE_GAP, check_ignore, fetch_image, fetch_images

ActivityImage = bilibili_activity.Activity[bilibili_activity.ContentImage]


async def get_appender(activity: ActivityImage) -> Callable[[Card], None]:
  image_infos = (
    activity.content.images[:9] if len(activity.content.images) > 9 else activity.content.images
  )
  avatar, images = await asyncio.gather(
    fetch_image(activity.avatar), fetch_images(*[image.src for image in image_infos])
  )

  def appender(card: Card) -> None:
    nonlocal images
    if len(images) == 1:
      cover = ImageOps.fit(images[0], (640, 400), imutil.resample())
    elif len(images) == 2:
      size = (640 - IMAGE_GAP) // 2
      image0 = ImageOps.fit(images[0], (size, size), imutil.resample())
      image1 = ImageOps.fit(images[1], (size, size), imutil.resample())
      cover = Image.new("RGB", (640, size), (255, 255, 255))
      cover.paste(image0, (0, 0))
      cover.paste(image1, (640 - size, 0))
    else:
      lines = math.ceil(len(images) / 3)
      size = (640 - 2 * IMAGE_GAP) // 3
      height = size * lines + max(lines - 1, 0) * IMAGE_GAP
      images = [ImageOps.fit(
        image, (size, size), imutil.resample()
      ) for image in images]
      cover = Image.new("RGB", (640, height), (255, 255, 255))
      for i, v in enumerate(images):
        y, x = divmod(i, 3)
        x = int(x / 2 * (640 - size))
        y = y * (size + IMAGE_GAP)
        cover.paste(v, (x, y))
    card.add(CardAuthor(avatar, activity.name))
    card.add(CardText(activity.content.text, 32, 3))
    card.add(CardCover(cover, False))

  return appender


async def format(activity: ActivityImage) -> Message:
  check_ignore(False, activity.content.text)
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card()
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 发布了动态\n"
      + imutil.to_segment(im)
      + f"\nhttps://t.bilibili.com/{activity.id}"
    )

  return await misc.to_thread(make)
