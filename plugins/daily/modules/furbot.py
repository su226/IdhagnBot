from nonebot.adapters.onebot.v11 import MessageSegment

from util import furbot_common

from . import Module


class FurbotModule(Module):
  async def format(self) -> MessageSegment:
    config = furbot_common.CONFIG()
    if not config.token:
      return MessageSegment.text("没有设置 Token，不能使用绒狸模块")
    picture = await furbot_common.get_daily_random()
    return MessageSegment.image(picture.url)
