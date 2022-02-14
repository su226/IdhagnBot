from typing import Any
from .. import util
import json

FORMAT = '''\
⭐ {username} 发布了动态
https://t.bilibili.com/{id}
“{summary}”'''

def handle(content: Any) -> str:
  card = json.loads(content["card"])
  return FORMAT.format(
    username=content["desc"]["user_profile"]["info"]["uname"],
    id=content["desc"]["dynamic_id_str"],
    summary=util.ellipsis(card["item"]["content"]))
