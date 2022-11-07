from datetime import datetime, timezone

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import epicgames

epicfree = command.CommandBuilder("epicfree", "epicfree", "epic", "e宝", "喜加一") \
  .brief("看看E宝又在送什么") \
  .usage('''\
/epicfree - 查看现在的免费游戏
你送游戏你是我宝，你卖游戏翻脸不认（雾）''') \
  .build()
@epicfree.handle()
async def handle_epicfree():
  games = await epicgames.free_games()
  if not games:
    await epicfree.finish("似乎没有可白嫖的游戏")
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
      MessageSegment.text(text + f"\n{epicgames.URL_BASE}{game.slug}\n"),
      MessageSegment.image(game.image)
    ])
  await epicfree.finish(Message(message))
