from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import steam_free as api

steam_free = command.CommandBuilder("steam_free", "steam") \
  .brief("看看Steam上在送什么免费游戏") \
  .usage("/steam - 查看现在的免费游戏") \
  .build()
@steam_free.handle()
async def handle_steam_free():
  games = await api.free_games()
  if not games:
    await steam_free.finish("似乎没有可白嫖的游戏")
  message = Message()
  for game in games:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.appid}\n"),
      MessageSegment.image(game.image),
    ])
  await steam_free.finish(Message(message))
