from collections import defaultdict
from typing import TypedDict
from nonebot.log import logger
import yaml
import os

class GroupTarget(TypedDict):
  group: int
class UserTarget(TypedDict):
  user: int
class User(TypedDict):
  uid: int
  name: str
  time: float
  targets: list[GroupTarget | UserTarget]
class Config(TypedDict):
  ellipsis: int
  interval: int
  users: list[User]

config: Config = {
  "ellipsis": 50,
  "interval": 600,
  "users": [],
}
if os.path.exists("configs/bilibili_activity.yaml"):
  with open("configs/bilibili_activity.yaml") as f:
    config |= yaml.load(f, yaml.CLoader)
else:
  logger.warning("配置文件不存在: configs/bilibili_activity.yaml")

groups: dict[int, list[int]] = defaultdict(list)
for user in config["users"]:
  if not isinstance(user["targets"], list):
    user["targets"] = [user["targets"]]
  for target in user["targets"]:
    if "group" in target:
      groups[target["group"]].append(user["uid"])
usernames: dict[int, str] = {}
timestamps: dict[int, int] = defaultdict(lambda: -1)

def ellipsis(content: str) -> str:
  if len(content) > config["ellipsis"]:
    return content[:config["ellipsis"] - 3] + "..."
  return content
