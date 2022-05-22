from typing import Any

FORMAT = '''\
🤔 {username} 发布了……一些东西
https://t.bilibili.com/{id}
目前机器人还不能理解这个qwq'''


def handle(content: Any) -> str:
  return FORMAT.format(
    username=content["desc"]["user_profile"]["info"]["uname"],
    id=content["desc"]["dynamic_id_str"])
