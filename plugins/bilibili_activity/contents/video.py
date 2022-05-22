import json
from typing import Any

from .. import util

FORMAT = '''\
[CQ:image,file={cover}]
🎞️ {username} 发布了视频
{link}
{activity}
---- 视频 ----
▶️ {title}
“{summary}”'''


def handle(content: Any) -> str:
  card = json.loads(content["card"])
  activity = card["dynamic"]
  if "new_topic" in content["display"]["topic_info"]:
    topic = content["display"]["topic_info"]["new_topic"]["name"]
    activity = f"#{topic}# {activity}"
  return FORMAT.format(
    cover=card["pic"],
    username=content["desc"]["user_profile"]["info"]["uname"],
    link=card["short_link"],
    activity=activity.strip(),
    title=card["title"],
    summary=util.ellipsis(card["desc"]))
