import asyncio
from typing import Callable

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common.bilibili_activity import ActivityVideo
from util.api_common.bilibili_activity.card import CardRichText, CardTopic, fetch_emotions
from util.images.card import Card, CardAuthor, CardCover, CardText

from .. import extras
from ..common import fetch_image


async def get_appender(activity: ActivityVideo[object]) -> Callable[[Card], None]:
  avatar, cover, emotions, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    fetch_emotions(activity.content.richtext),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    if activity.content.richtext:
      block.add(CardRichText(activity.content.richtext, emotions, 32, 3, activity.topic))
    else:
      block.add(CardTopic(activity.topic))
    if activity.content.title:  # 动态视频没有标题
      block.add(CardText(activity.content.title, 40, 2))
    card.add(block)
    card.add(CardCover(cover))
    if activity.content.desc and activity.content.desc != "-":
      block = Card()
      block.add(CardText(activity.content.desc, 32, 3))
      append_extra(block, False)
      card.add(block)
    else:
      append_extra(card, True)

  return appender


async def format(activity: ActivityVideo[object], can_ignore: bool) -> Message:
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
