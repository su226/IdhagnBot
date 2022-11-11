import asyncio

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from PIL import Image

from util import command, context, imutil
from util.images.leaderboard import render as render_leaderboard

from .config import STATE

WIDTH = 640
HEIGHTS = [140, 100, 100, 80]
MIN_LINES = 6


# 草，走，忽略
leaderboard = (
  command.CommandBuilder("sign.leaderboard", "签到排名", "签到排行")
  .in_group()
  .brief("查看签到排名")
  .build()
)
@leaderboard.handle()
async def handle_leaderboard(bot: Bot, event: MessageEvent) -> None:
  async def fetch_data(uid: int) -> tuple[Image.Image, str, str]:
    avatar, name = await asyncio.gather(
      imutil.get_avatar(uid),
      context.get_card_or_name(bot, event, uid)
    )
    user_data = group_data.get_user(uid)
    time = user_data.time.strftime("%H:%M:%S")
    return avatar, name, time

  group_data = STATE(context.get_event_context(event))
  group_data.update()
  data: list[tuple[Image.Image, str, str]] = await asyncio.gather(
    *(fetch_data(uid) for uid in group_data.rank)
  )

  def make() -> MessageSegment:
    im = render_leaderboard(data)
    return imutil.to_segment(im)

  await leaderboard.finish(await asyncio.to_thread(make))
