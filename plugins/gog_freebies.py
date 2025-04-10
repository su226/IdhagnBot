from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import gog_freebies as api

gog_freebies = command.CommandBuilder("gog_freebies", "gog") \
  .brief("看看GOG上在送什么免费游戏") \
  .usage("/gog - 查看现在的免费游戏") \
  .build()
@gog_freebies.handle()
async def handle_gog_freebies():
  games = await api.get_freebies()
  if not games:
    await gog_freebies.finish("似乎没有可白嫖的游戏")
  message = Message()
  for game in games:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{game.name}\n{api.URL_BASE}{game.slug}\n"),
      MessageSegment.image(game.image),
    ])
  await gog_freebies.finish(Message(message))
