from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import fab_free as api

fab_free = command.CommandBuilder("fab_free", "fab") \
  .brief("看看E宝又在送什么资产") \
  .usage('''\
/fab - 查看现在的免费资产
你送资产你是我宝，你卖引擎我翻脸不认（雾）''') \
  .build()
@fab_free.handle()
async def handle_fab_free():
  assets = await api.free_assets()
  if not assets:
    await fab_free.finish("似乎没有可白嫖的资产")
  message = Message()
  for asset in assets:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(f"{wrap}{asset.title}\n{api.URL_BASE}{asset.uid}\n"),
      MessageSegment.image(asset.image),
    ])
  await fab_free.finish(Message(message))
