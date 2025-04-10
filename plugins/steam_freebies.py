from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import steam_freebies as api

steam_freebies = command.CommandBuilder("steam_freebies", "steam") \
  .brief("看看Steam上在送什么免费游戏") \
  .usage("/steam - 查看现在的免费游戏") \
  .build()
@steam_freebies.handle()
async def handle_steam_freebies():
  games = await api.get_freebies()
  if not games:
    await steam_freebies.finish("似乎没有可白嫖的游戏")
  message = Message()
  for game in games:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.appid}\n"),
      MessageSegment.image(game.image),
    ])
  await steam_freebies.finish(Message(message))
