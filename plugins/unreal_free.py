from nonebot.adapters.onebot.v11 import Message, MessageSegment

from util import command
from util.api_common import unreal_free as api

unreal_free = command.CommandBuilder("unreal_free", "虚幻资产", "虚幻", "unreal") \
  .brief("看看E宝又在送什么虚幻资产") \
  .usage('''\
/unrealfree - 查看现在的免费资产
你送资产你是我宝，你卖引擎我翻脸不认（雾）''') \
  .build()
@unreal_free.handle()
async def handle_unrealfree():
  assets = await api.free_assets()
  if not assets:
    await unreal_free.finish("似乎没有可白嫖的资产")
  message = Message()
  for asset in assets:
    wrap = "\n" if message else ""
    message.extend([
      MessageSegment.text(
        f"{wrap}{asset.category}资产 {asset.title} 原价 {asset.price} 现在免费，"
        f"共 {asset.ratingCount} 条评价，平均 {asset.ratingScore}⭐\n"
        f"{api.URL_BASE}{asset.slug}\n"
      ),
      MessageSegment.image(asset.image)
    ])
  await unreal_free.finish(Message(message))
