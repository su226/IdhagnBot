import json
from typing import Any, Callable

from .. import util

FORMAT = '''\
👀 {username} 转发了 {fromuser} 的{type}
https://t.bilibili.com/{id}
“{summary}”
---- 原{type} ----
{original}'''


def gallery(original: str) -> str:
  card = json.loads(original)
  text = card["item"]["description"]
  util.check_ignore(True, text)
  return '''\
🖼️ {image_count} 张图片
“{summary}”'''.format(
    image_count=len(card["item"]["pictures"]),
    summary=util.ellipsis(text))


def activity(original: str) -> str:
  card = json.loads(original)
  text = card["item"]["content"]
  util.check_ignore(True, text)
  return "“{summary}”".format(summary=util.ellipsis(text))


def video(original: str) -> str:
  card = json.loads(original)
  return '''\
▶️ {title}
“{summary}”'''.format(
    title=card["title"],
    summary=util.ellipsis(card["desc"]))


def article(original: str) -> str:
  card = json.loads(original)
  return '''\
👓 {title}
“{summary}”'''.format(
    title=card["title"],
    summary=util.ellipsis(card["summary"]))


FormatterType = Callable[[str], str]
ORIGINAL_FORMAT: dict[int, tuple[str, FormatterType]] = {
  2: ("动态", gallery),
  4: ("动态", activity),
  8: ("视频", video),
  64: ("专栏", article)
}
ORIGINAL_UNKNOWN: tuple[str, FormatterType] = ("动态", lambda _: "目前机器人还不能理解这个qwq")


def handle(content: Any) -> str:
  card = json.loads(content["card"])
  orig_type, orig_formatter = ORIGINAL_FORMAT.get(card["item"]["orig_type"], ORIGINAL_UNKNOWN)
  text = card["item"]["content"]
  util.check_ignore(False, text)
  return FORMAT.format(
    username=content["desc"]["user_profile"]["info"]["uname"],
    fromuser=card["origin_user"]["info"]["uname"],
    id=content["desc"]["dynamic_id_str"],
    summary=util.ellipsis(text),
    type=orig_type,
    original=orig_formatter(card["origin"]))
