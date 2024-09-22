import asyncio
import time
from typing import Any, Awaitable, Callable, List, Optional, Tuple, Type, TypeVar, Union

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from util import imutil, misc
from util.api_common.bilibili_activity import (
  Activity, ActivityCourse, ActivityForward, ActivityLive, ActivityLiveRcmd, ActivityPGC,
  ActivityPlaylist, ContentArticle, ContentAudio, ContentCommon, ContentCourse, ContentImage,
  ContentLive, ContentLiveRcmd, ContentPGC, ContentPlaylist, ContentText, ContentVideo,
  RichTextLottery,
)
from util.api_common.bilibili_activity.card import CardRichText, CardTopic, fetch_emotions
from util.images.card import Card, CardAuthor, CardCover, CardLine, CardText

from .. import extras
from ..common import CONFIG, IgnoredException, check_ignore, fetch_image
from . import article, audio, common, image, text, video

TContent = TypeVar("TContent")
Checker = Tuple[Type[TContent], Callable[[TContent], None]]
TitleFormatter = Tuple[Type[TContent], Callable[[TContent], str]]
AppenderGetter = Tuple[Type[TContent], Callable[[TContent], Awaitable[Callable[[Card], None]]]]


def make_title_formatter(label: str) -> Callable[[Activity[object, object]], str]:
  def title_formatter(activity: Activity[object, object]) -> str:
    return f" {activity.name} 的{label}"
  return title_formatter


def pgc_title_formatter(activity: ActivityPGC[object]) -> str:
  if activity.content.label:
    prefix = activity.content.label
  else:
    prefix = ""
  return prefix + " " + activity.content.season_name


def checker(activity: Union[text.ActivityText[object], image.ActivityImage[object]]) -> None:
  config = CONFIG()
  if config.ignore_forward_lottery:
    for node in activity.content.richtext:
      if isinstance(node, RichTextLottery):
        raise IgnoredException(node)
  for regex in config.ignore_forward_regexs:
    if regex.search(activity.content.text):
      raise IgnoredException(regex)


async def get_pgc_appender(activity: ActivityPGC[object]) -> Callable[[Card], None]:
  async def fetch_season_cover() -> Optional[Image.Image]:
    if activity.avatar:
      return await fetch_image(activity.avatar)
    if activity.content.season_cover:
      return await fetch_image(activity.content.season_cover)
    return None

  season_cover, episode_cover, append_extra = await asyncio.gather(
    fetch_season_cover(),
    fetch_image(activity.content.episode_cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    if season_cover:
      block.add(CardAuthor(season_cover, activity.content.season_name))
    else:
      block.add(CardText(activity.content.season_name, size=32, lines=1))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.episode_name, size=40, lines=2))
    card.add(block)
    card.add(CardCover(episode_cover))
    append_extra(card, True)

  return appender


async def get_live_appender(activity: ActivityLive[object]) -> Callable[[Card], None]:
  avatar, cover, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.title, size=40, lines=2))
    streaming = "直播中" if activity.content.streaming else "已下播"
    block.add(CardText(f"{activity.content.category} {streaming}", size=32, lines=0))
    card.add(block)
    card.add(CardCover(cover))
    append_extra(card, True)

  return appender


async def get_live_rcmd_appender(activity: ActivityLiveRcmd[object]) -> Callable[[Card], None]:
  avatar, cover, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.title, size=40, lines=2))
    start_time = time.strftime("%m-%d %H:%M", time.localtime(activity.content.start_time))
    block.add(CardText((
      f"{activity.content.parent_category}/{activity.content.category} "
      f"{activity.content.watching} 人看过\n"
      f"{start_time} 开播"
    ), size=32, lines=0))
    card.add(block)
    card.add(CardCover(cover))
    append_extra(card, True)

  return appender


async def get_course_appender(activity: ActivityCourse[object]) -> Callable[[Card], None]:
  async def fetch_avatar() -> Optional[Image.Image]:
    if activity.avatar:
      return await fetch_image(activity.avatar)
    return None

  avatar, cover, append_extra = await asyncio.gather(
    fetch_avatar(),
    fetch_image(activity.content.cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    if avatar:
      block.add(CardAuthor(avatar, activity.name))
    else:
      block.add(CardText("@" + activity.name, size=32, lines=1))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.title, size=40, lines=2))
    block.add(CardText(activity.content.stat, size=32, lines=0))
    card.add(block)
    card.add(CardCover(cover))
    block = Card()
    block.add(CardText(activity.content.desc, size=32, lines=3))
    append_extra(block, False)
    card.add(block)

  return appender


async def get_playlist_appender(activity: ActivityPlaylist[object]) -> Callable[[Card], None]:
  avatar, cover, append_extra = await asyncio.gather(
    fetch_image(activity.avatar),
    fetch_image(activity.content.cover),
    extras.format(activity.extra),
  )

  def appender(card: Card) -> None:
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardTopic(activity.topic))
    block.add(CardText(activity.content.title, size=40, lines=2))
    block.add(CardText(activity.content.stat, size=32, lines=0))
    card.add(block)
    card.add(CardCover(cover))
    append_extra(card, True)

  return appender


async def get_deleted_appender(reason: str) -> Callable[[Card], None]:
  def appender(card: Card) -> None:
    block = Card()
    message = "源动态已失效"
    if reason:
      message += f"（{reason}）"
    block.add(CardText(message, size=32, lines=0))
    card.add(block)
  return appender


async def get_unknown_appender(activity: Activity[object, object]) -> Callable[[Card], None]:
  def appender(card: Card) -> None:
    block = Card()
    block.add(CardText(f"IdhagnBot 暂不支持解析此类动态（{activity.type}）", size=32, lines=0))
    card.add(block)
  return appender


GENERIC_TITLE = make_title_formatter("动态")
CHECKERS: List[Checker[Any]] = [
  (ContentText, checker),
  (ContentImage, checker),
]
TITLE_FORMATTERS: List[TitleFormatter[Any]] = [
  (ContentVideo, make_title_formatter("视频")),
  (ContentAudio, make_title_formatter("音频")),
  (ContentArticle, make_title_formatter("专栏")),
  (ContentPGC, pgc_title_formatter),
  (ContentLive, make_title_formatter("直播")),
  (ContentLiveRcmd, make_title_formatter("直播")),
  (ContentCourse, make_title_formatter("课程")),
  (ContentPlaylist, make_title_formatter("合集")),
]
CARD_APPENDERS: List[AppenderGetter[Any]] = [
  (ContentText, text.get_appender),
  (ContentImage, image.get_appender),
  (ContentVideo, video.get_appender),
  (ContentAudio, audio.get_appender),
  (ContentArticle, article.get_appender),
  (ContentCommon, common.get_appender),
  (ContentPGC, get_pgc_appender),
  (ContentLive, get_live_appender),
  (ContentLiveRcmd, get_live_rcmd_appender),
  (ContentCourse, get_course_appender),
  (ContentPlaylist, get_playlist_appender),
]


async def format(activity: ActivityForward[object], can_ignore: bool) -> Message:
  if can_ignore:
    check_ignore(activity.content.text)

  if activity.content.activity is None:
    title_label = "失效动态"
  else:
    if can_ignore:
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

  if activity.content.activity is None:
    appender_coro = get_deleted_appender(activity.content.error_text)
  else:
    for type, getter in CARD_APPENDERS:
      if isinstance(activity.content.activity.content, type):
        appender_coro = getter(activity.content.activity)
        break
    else:
      appender_coro = get_unknown_appender(activity.content.activity)

  avatar, appender, emotions, append_extras = await asyncio.gather(
    fetch_image(activity.avatar),
    appender_coro,
    fetch_emotions(activity.content.richtext),
    extras.format(activity.extra),
  )

  def make() -> Message:
    card = Card(0)
    block = Card()
    block.add(CardAuthor(avatar, activity.name))
    block.add(CardRichText(activity.content.richtext, emotions, 32, 3, activity.topic))
    append_extras(block, False)
    card.add(block)
    card.add(CardLine())
    appender(card)
    im = Image.new("RGB", (card.get_width(), card.get_height()), (255, 255, 255))
    card.render(im, 0, 0)
    return Message([
      MessageSegment.text(f"{activity.name} 转发了{title_label}\n"),
      imutil.to_segment(im),
      MessageSegment.text(f"\nhttps://t.bilibili.com/{activity.id}"),
    ])

  return await misc.to_thread(make)
