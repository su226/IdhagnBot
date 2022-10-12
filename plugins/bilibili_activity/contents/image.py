import asyncio
import math
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image, ImageOps

from util import bilibili_activity, util
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import IMAGE_GAP, check_ignore, fetch_image

ActivityImage = bilibili_activity.Activity[bilibili_activity.ContentImage]


async def append_card(activity: ActivityImage, card: Card) -> None:
  image_infos = activity.content.images[:9] \
    if len(activity.content.images) > 9 else activity.content.images
  coros = [fetch_image(activity.avatar)]
  coros.extend([fetch_image(image.src) for image in image_infos])
  avatar, *images = await asyncio.gather(*coros)
  if len(images) == 1:
    cover = ImageOps.fit(images[0], (640, 400), util.resample)
  elif len(images) == 2:
    size = (640 - IMAGE_GAP) // 2
    image0 = ImageOps.fit(images[0], (size, size), util.resample)
    image1 = ImageOps.fit(images[1], (size, size), util.resample)
    cover = Image.new("RGB", (640, size), (255, 255, 255))
    cover.paste(image0, (0, 0))
    cover.paste(image1, (640 - size, 0))
  else:
    lines = math.ceil(len(images) / 3)
    size = (640 - 2 * IMAGE_GAP) // 3
    height = size * lines + max(lines - 1, 0) * IMAGE_GAP
    images = [ImageOps.fit(
      image, (size, size), util.resample
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


async def format(activity: ActivityImage) -> Message:
  check_ignore(False, activity.content.text)
  card = Card()
  await append_card(activity, card)
  im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
  card.render(im, 0, 0)
  f = BytesIO()
  im.save(f, "PNG")
  return \
    f"{activity.name} 发布了动态\n" + \
    MessageSegment.image(f) + \
    f"\nhttps://t.bilibili.com/{activity.id}"
