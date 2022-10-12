import asyncio
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image, ImageOps

from util import bilibili_activity, util
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import IMAGE_GAP, fetch_image

ActivityArticle = bilibili_activity.Activity[bilibili_activity.ContentArticle]


async def append_card(activity: ActivityArticle, card: Card) -> None:
  avatar, *covers = await asyncio.gather(*[
    fetch_image(url) for url in [activity.avatar, *activity.content.covers]
  ])
  if len(covers) == 1:
    cover = covers[0]
  else:
    gaps = len(covers) - 1
    size = 640 - gaps * IMAGE_GAP
    covers = [ImageOps.fit(
      cover, (size, size), util.resample
    ) for cover in covers]
    cover = Image.new("RGB", (640, size), (255, 255, 255))
    for i, v in enumerate(covers):
      cover.paste(v, (i * (size + IMAGE_GAP), 0))
  card.add(CardAuthor(avatar, activity.name))
  card.add(CardText(activity.content.title, 40, 2))
  card.add(CardCover(cover, False))
  card.add(CardText(activity.content.desc, 32, 3))


async def format(activity: ActivityArticle) -> Message:
  card = Card()
  await append_card(activity, card)
  im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
  card.render(im, 0, 0)
  f = BytesIO()
  im.save(f, "PNG")
  return \
    f"{activity.name} 发布了专栏\n" + \
    MessageSegment.image(f) + \
    f"\nhttps://www.bilibili.com/read/cv{activity.content.id}"
