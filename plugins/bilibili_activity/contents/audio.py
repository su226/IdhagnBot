import asyncio
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from util import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardText

from ..common import fetch_image

ActivityAudio = bilibili_activity.Activity[bilibili_activity.ContentAudio]


async def append_card(activity: ActivityAudio, card: Card) -> None:
  avatar, cover = await asyncio.gather(
    fetch_image(activity.avatar), fetch_image(activity.content.cover))
  card.add(CardAuthor(avatar, activity.name))
  card.add(CardText(activity.content.title, 40, 2))
  card.add(CardText(activity.content.label, 32, 1))
  card.add(CardCover(cover))
  if activity.content.desc and activity.content.desc != "-":
    card.add(CardText(activity.content.desc, 32, 3))


async def format(activity: ActivityAudio) -> Message:
  card = Card()
  await append_card(activity, card)
  im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
  card.render(im, 0, 0)
  f = BytesIO()
  im.save(f, "PNG")
  return \
    f"{activity.name} 发布了音频\n" + \
    MessageSegment.image(f) + \
    f"\nhttps://www.bilibili.com/audio/au{activity.content.id}"
