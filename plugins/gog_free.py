from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import gog_free as api

gog_free = command.CommandBuilder("gog_free", "gog") \
  .brief("看看GOG上在送什么免费游戏") \
  .usage("/gog - 查看现在的免费游戏") \
  .build()
@gog_free.handle()
async def handle_gog_free():
  games = await api.free_games()
  if not games:
    await gog_free.finish("似乎没有可白嫖的游戏")
  message = Message()
  for game in games:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.slug}\n"),
      MessageSegment.image(game.image),
    ])
  await gog_free.finish(Message(message))
