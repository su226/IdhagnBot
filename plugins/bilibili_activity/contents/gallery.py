from typing import Any
from .. import util
import json

FORMAT = '''\
[CQ:image,file={image}]
⭐ {username} 发布了动态
https://t.bilibili.com/{id}
🖼️ {image_count} 张图片
“{summary}”'''

def handle(content: Any) -> str:
  card = json.loads(content["card"])
  text = card["item"]["description"]
  util.check_ignore(False, text)
  return FORMAT.format(
    image=card["item"]["pictures"][0]["img_src"],
    username=content["desc"]["user_profile"]["info"]["uname"],
    id=content["desc"]["dynamic_id_str"],
    image_count=len(card["item"]["pictures"]),
    summary=util.ellipsis(text))
