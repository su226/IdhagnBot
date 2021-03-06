import json
from typing import Any

from .. import util

FORMAT = '''\
[CQ:image,file={cover}]
π° {username} εεΈδΊδΈζ 
https://www.bilibili.com/read/cv{id}
π {title}
β{summary}β'''


def handle(content: Any) -> str:
  card = json.loads(content["card"])
  return FORMAT.format(
    cover=card["image_urls"][0],
    username=content["desc"]["user_profile"]["info"]["uname"],
    id=card["id"],
    title=card["title"],
    summary=util.ellipsis(card["summary"]))
