from typing import Any, Awaitable, Callable, List, Tuple, Type, Union

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from util import imutil, misc
from util.api_common import bilibili_activity
from util.images.card import Card, CardAuthor, CardCover, CardLine, CardText

from ..common import TContent, check_ignore, fetch_image
from . import article, audio, image, text, video

Checker = Tuple[Type[TContent], Callable[[TContent], None]]
TitleFormatter = Tuple[Type[TContent], Callable[[TContent], str]]
AppenderGetter = Tuple[Type[TContent], Callable[[TContent], Awaitable[Callable[[Card], None]]]]
ActivityPGC = bilibili_activity.Activity[bilibili_activity.ContentPGC]


def make_title_formatter(label: str) -> Callable[[bilibili_activity.Activity[Any]], str]:
  def title_formatter(activity: bilibili_activity.Activity[Any]) -> str:
    return f" {activity.name} 的{label}"
  return title_formatter


def pgc_title(activity: ActivityPGC) -> str:
  if activity.content.label:
    return activity.content.label
  return " " + activity.content.season_name


def checker(activity: Union[text.ActivityText, image.ActivityImage]) -> None:
  check_ignore(True, activity.content.text)


async def get_pgc_appender(activity: ActivityPGC) -> Callable[[Card], None]:
  if activity.content.season_cover:
    season_cover = await fetch_image(activity.content.season_cover)
  else:
    season_cover = None
  episode_cover = await fetch_image(activity.content.episode_cover)

  def appender(card: Card) -> None:
    if season_cover:
      card.add(CardAuthor(season_cover, activity.content.season_name))
    else:
      card.add(CardText(activity.content.season_name, 32, 1))
    card.add(CardText(activity.content.episode_name, 40, 2))
    card.add(CardCover(episode_cover))

  return appender


def deleted_appender(card: Card) -> None:
  card.add(CardText("源动态已失效", 32, 2))


def unknown_appender(card: Card) -> None:
  card.add(CardText("IdhagnBot 暂不支持解析此类动态", 32, 2))


GENERIC_TITLE = make_title_formatter("动态")
CHECKERS: List[Checker[Any]] = [
  (bilibili_activity.ContentText, checker),
  (bilibili_activity.ContentImage, checker),
]
TITLE_FORMATTERS: List[TitleFormatter[Any]] = [
  (bilibili_activity.ContentVideo, make_title_formatter("视频")),
  (bilibili_activity.ContentAudio, make_title_formatter("音频")),
  (bilibili_activity.ContentArticle, make_title_formatter("专栏")),
  (bilibili_activity.ContentPGC, pgc_title),
]
CARD_APPENDERS: List[AppenderGetter[Any]] = [
  (bilibili_activity.ContentText, text.get_appender),
  (bilibili_activity.ContentImage, image.get_appender),
  (bilibili_activity.ContentVideo, video.get_appender),
  (bilibili_activity.ContentAudio, audio.get_appender),
  (bilibili_activity.ContentArticle, article.get_appender),
  (bilibili_activity.ContentPGC, get_pgc_appender),
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

  if activity.content.activity is None:
    appender = deleted_appender
  else:
    for type, getter in CARD_APPENDERS:
      if isinstance(activity.content.activity.content, type):
        appender = await getter(activity.content.activity)
        break
    else:
      appender = unknown_appender

  def make() -> Message:
    card = Card()
    card.add(CardAuthor(avatar, activity.name))
    card.add(CardText(activity.content.text, 32, 3))
    card.add(CardLine())
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return (
      f"{activity.name} 转发了{title_label}\n"
      + imutil.to_segment(im)
      + f"\nhttps://t.bilibili.com/{activity.id}"
    )

  return await misc.to_thread(make)
