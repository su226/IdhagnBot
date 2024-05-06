import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image, ImageOps

from util import imutil, misc, textutil
from util.api_common.bilibili_activity import ActivityCommonSquare
from util.api_common.bilibili_activity.card import CardRichText, fetch_emotions
from util.images.card import Card, CardAuthor, CardMargin, CardTab

from .. import extras
from ..common import check_ignore, fetch_image


async def get_appender(activity: ActivityCommonSquare[object]) -> Callable[[Card], None]:
  avatar, cover, emotions, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    fetch_emotions(activity.content.richtext),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardRichText(activity.content.richtext, emotions, 32, 6, activity.topic))
    block.add(CardMargin())
    content = (
      f"{textutil.escape(activity.content.title)}\n"
      f"<span color='#888888'>{textutil.escape(activity.content.desc)}</span>"
    )
    nonlocal cover
    cover = ImageOps.fit(cover, (100, 100), imutil.scale_resample())
    block.add(CardTab(content, activity.content.badge, cover))
    append_extra(block, False)
    card.add(block)

  return appender


async def format(activity: ActivityCommonSquare[object], can_ignore: bool) -> Message:
  if can_ignore:
    check_ignore(False, activity.content.text)
  appender = await get_appender(activity)

  def make() -> Message:
    card = Card(0)
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return Message([
      f"{activity.name} 发布了动态\n",
      imutil.to_segment(im),
      f"\nhttps://t.bilibili.com/{activity.id}"
    ])

  return await misc.to_thread(make)
