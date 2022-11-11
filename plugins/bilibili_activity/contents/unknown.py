from typing import Any

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util.api_common import bilibili_activity


async def format(activity: bilibili_activity.Activity[Any]) -> Message:
  return Message(MessageSegment.text(
    f"{activity.name} 发布了动态\n"
    "IdhagnBot 暂不支持解析此类动态\n"
    f"https://t.bilibili.com/{activity.id}"
  ))
