import asyncio
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from util import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import fetch_image

ActivityVideo = bilibili_activity.Activity[bilibili_activity.ContentVideo]


async def append_card(activity: ActivityVideo, card: Card) -> None:
  avatar, cover = await asyncio.gather(
    fetch_image(activity.avatar), fetch_image(activity.content.cover))
  card.add(CardAuthor(avatar, activity.name))
  if activity.content.text:
    card.add(CardText(activity.content.text, 32, 3))
  card.add(CardText(activity.content.title, 40, 2))
  card.add(CardCover(cover))
  if activity.content.desc and activity.content.desc != "-":
    card.add(CardText(activity.content.desc, 32, 3))


async def format(activity: ActivityVideo) -> Message:
  card = Card()
  await append_card(activity, card)
  im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
  card.render(im, 0, 0)
  f = BytesIO()
  im.save(f, "PNG")
  return \
    f"{activity.name} 发布了视频\n" + \
    MessageSegment.image(f) + \
    f"\nhttps://www.bilibili.com/video/{activity.content.bvid}"
