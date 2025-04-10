from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import fab_freebies as api

fab_freebies = command.CommandBuilder("fab_freebies", "fab") \
  .brief("看看E宝又在送什么资产") \
  .usage('''\
/fab - 查看现在的免费资产
你送资产你是我宝，你卖引擎我翻脸不认（雾）''') \
  .build()
@fab_freebies.handle()
async def handle_fab_freebies():
  assets = await api.get_freebies()
  if not assets:
    await fab_freebies.finish("似乎没有可白嫖的资产")
  message = Message()
  for asset in assets:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{asset.name}\n{api.URL_BASE}{asset.uid}\n"),
      MessageSegment.image(asset.image),
    ])
  await fab_freebies.finish(Message(message))
