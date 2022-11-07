from loguru import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util.api_common import furbot

from . import Module


class FurbotModule(Module):
  async def format(self) -> list[Message]:
    config = furbot.CONFIG()
    if not config.token:
      logger.warning("没有设置 Token，不能使用绒狸模块")
      return []
    picture = await furbot.get_daily_random()
    return [Message(MessageSegment.image(picture.url))]
