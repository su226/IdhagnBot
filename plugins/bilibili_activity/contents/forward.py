from io import BytesIO
from typing import Any, Awaitable, Callable

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from util import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardLine, CardText

from ..common import TContent, check_ignore, fetch_image
from . import article, audio, image, text, video

Checker = tuple[type[TContent], Callable[[TContent], None]]
TitleFormatter = tuple[type[TContent], Callable[[TContent], str]]
CardAppender = tuple[type[TContent], Callable[[TContent, Card], Awaitable[None]]]
ActivityPGC = bilibili_activity.Activity[bilibili_activity.ContentPGC]


def make_title_formatter(label: str) -> Callable[[bilibili_activity.Activity[Any]], str]:
  def title_formatter(activity: bilibili_activity.Activity[Any]) -> str:
    return f" {activity.name} 的{label}"
  return title_formatter


def pgc_title(activity: ActivityPGC) -> str:
  if activity.content.label:
    return activity.content.label
  return " " + activity.content.season_name


def checker(activity: text.ActivityText | image.ActivityImage) -> None:
  check_ignore(True, activity.content.text)


async def append_pgc_card(activity: ActivityPGC, card: Card) -> None:
  if activity.content.season_cover:
    season_cover = await fetch_image(activity.content.season_cover)
    card.add(CardAuthor(season_cover, activity.content.season_name))
  else:
    card.add(CardText(activity.content.season_name, 32, 1))
  card.add(CardText(activity.content.episode_name, 40, 2))
  episode_cover = await fetch_image(activity.content.episode_cover)
  card.add(CardCover(episode_cover))


GENERIC_TITLE = make_title_formatter("动态")
CHECKERS: list[Checker[Any]] = [
  (bilibili_activity.ContentText, checker),
  (bilibili_activity.ContentImage, checker),
]
TITLE_FORMATTERS: list[TitleFormatter[Any]] = [
  (bilibili_activity.ContentVideo, make_title_formatter("视频")),
  (bilibili_activity.ContentAudio, make_title_formatter("音频")),
  (bilibili_activity.ContentArticle, make_title_formatter("专栏")),
  (bilibili_activity.ContentPGC, pgc_title),
]
CARD_APPENDERS: list[CardAppender[Any]] = [
  (bilibili_activity.ContentText, text.append_card),
  (bilibili_activity.ContentImage, image.append_card),
  (bilibili_activity.ContentVideo, video.append_card),
  (bilibili_activity.ContentAudio, audio.append_card),
  (bilibili_activity.ContentArticle, article.append_card),
  (bilibili_activity.ContentPGC, append_pgc_card),
]


async def format(
  activity: bilibili_activity.Activity[bilibili_activity.ContentForward]
) -> Message:
  check_ignore(False, activity.content.text)

  if activity.content.activity is None:
    title_label = "失效动态"
  else:
    for type, checker in CHECKERS:
      if isinstance(activity.content.activity.content, type):
        checker(activity.content.activity)
        break

    for type, formatter in TITLE_FORMATTERS:
      if isinstance(activity.content.activity.content, type):
        title_label = formatter(activity.content.activity)
        break
    else:
      title_label = GENERIC_TITLE(activity.content.activity)

  avatar = await fetch_image(activity.avatar)
  card = Card()
  card.add(CardAuthor(avatar, activity.name))
  card.add(CardText(activity.content.text, 32, 3))
  card.add(CardLine())

  if activity.content.activity is None:
    card.add(CardText("源动态已失效", 32, 2))
  else:
    for type, appender in CARD_APPENDERS:
      if isinstance(activity.content.activity.content, type):
        await appender(activity.content.activity, card)
        break
    else:
      card.add(CardText("IdhagnBot 暂不支持解析此类动态", 32, 2))

  im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
  card.render(im, 0, 0)
  f = BytesIO()
  im.save(f, "PNG")

  return \
    f"{activity.name} 转发了{title_label}\n" + \
    MessageSegment.image(f) + \
    f"\nhttps://t.bilibili.com/{activity.id}"
