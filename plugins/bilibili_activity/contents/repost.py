import json
from typing import Any, Callable

from .. import util

FORMAT = '''\
๐ {username} ่ฝฌๅไบ {fromuser} ็{type}
https://t.bilibili.com/{id}
โ{summary}โ
---- ๅ{type} ----
{original}'''


def gallery(original: str) -> str:
  card = json.loads(original)
  text = card["item"]["description"]
  util.check_ignore(True, text)
  return '''\
๐ผ๏ธ {image_count} ๅผ ๅพ็
โ{summary}โ'''.format(
    image_count=len(card["item"]["pictures"]),
    summary=util.ellipsis(text))


def activity(original: str) -> str:
  card = json.loads(original)
  text = card["item"]["content"]
  util.check_ignore(True, text)
  return "โ{summary}โ".format(summary=util.ellipsis(text))


def video(original: str) -> str:
  card = json.loads(original)
  return '''\
โถ๏ธ {title}
โ{summary}โ'''.format(
    title=card["title"],
    summary=util.ellipsis(card["desc"]))


def article(original: str) -> str:
  card = json.loads(original)
  return '''\
๐ {title}
โ{summary}โ'''.format(
    title=card["title"],
    summary=util.ellipsis(card["summary"]))


FormatterType = Callable[[str], str]
ORIGINAL_FORMAT: dict[int, tuple[str, FormatterType]] = {
  2: ("ๅจๆ", gallery),
  4: ("ๅจๆ", activity),
  8: ("่ง้ข", video),
  64: ("ไธๆ ", article)
}
ORIGINAL_UNKNOWN: tuple[str, FormatterType] = ("ๅจๆ", lambda _: "็ฎๅๆบๅจไบบ่ฟไธ่ฝ็่งฃ่ฟไธชqwq")


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
