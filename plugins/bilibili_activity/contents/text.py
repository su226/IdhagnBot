from io import BytesIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from util import bilibili_activity
from util.images.card import Card, CardAuthor, CardText

from ..common import check_ignore, fetch_image

ActivityText = bilibili_activity.Activity[bilibili_activity.ContentText]


async def append_card(activity: ActivityText, card: Card) -> None:
  avatar = await fetch_image(activity.avatar)
  card.add(CardAuthor(avatar, activity.name))
  card.add(CardText(activity.content.text, 32, 6))


async def format(activity: ActivityText) -> Message:
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
