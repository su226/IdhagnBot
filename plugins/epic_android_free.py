from datetime import datetime, timezone

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import epic_android_free as api

epic_android_free = command.CommandBuilder(
  "epic_android_free", "epicgames安卓", "epic安卓", "e宝安卓", "喜加一安卓",
) \
  .brief("看看E宝又在送什么安卓游戏") \
  .usage('''\
/epicgames - 查看现在的免费安卓游戏
你送游戏你是我宝，你卖游戏翻脸不认（雾）''') \
  .build()
@epic_android_free.handle()
async def handle_epicfree():
  games = await api.free_games()
  if not games:
    await epic_android_free.finish("似乎没有可白嫖的游戏")
  games.sort(key=lambda x: x.end_date)
  now_date = datetime.now(timezone.utc)
  message = Message()
  for game in games:
    end_str = game.end_date.astimezone().strftime("%Y-%m-%d %H:%M")
    if now_date > game.start_date:
      text = f"{game.title} 目前免费，截止到 {end_str}"
    else:
      start_str = game.start_date.astimezone().strftime("%Y-%m-%d %H:%M")
      text = f"{game.title} 将在 {start_str} 免费，截止到 {end_str}"
    if message:
      text = "\n" + text
    message.extend([
      MessageSegment.text(text),
      MessageSegment.image(game.image),
    ])
  await epic_android_free.finish(Message(message))
