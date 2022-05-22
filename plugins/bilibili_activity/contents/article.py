import json
from typing import Any

from .. import util

FORMAT = '''\
[CQ:image,file={cover}]
📰 {username} 发布了专栏
https://www.bilibili.com/read/cv{id}
👓 {title}
“{summary}”'''


def handle(content: Any) -> str:
  card = json.loads(content["card"])
  return FORMAT.format(
    cover=card["image_urls"][0],
    username=content["desc"]["user_profile"]["info"]["uname"],
    id=card["id"],
    title=card["title"],
    summary=util.ellipsis(card["summary"]))
