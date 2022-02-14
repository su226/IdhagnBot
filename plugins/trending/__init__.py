import math
from . import baidu, cctv, weibo, zhihu, bilibili
from .common import Item
from util.config import BaseConfig, BaseState, BaseModel, Field
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import MessageSegment
import nonebot
import time

class Config(BaseConfig):
  __file__ = "trending"
  cache: int = 600
  page_size: int = 10

class Cache(BaseModel):
  time: float = 0
  items: list[Item] = Field(default_factory=list)

class State(BaseState):
  __file__ = "trending"
  cache: dict[str, Cache] = Field(default_factory=dict)

CONFIG = Config.load()
STATE = State.load()
SOURCE_LIST = [
  (["百度", "baidu"], baidu.get_data),
  (["央视", "cctv"], cctv.get_data),
  (["微博", "weibo"], weibo.get_data),
  (["知乎", "zhihu"], zhihu.get_data),
  (["哔哩哔哩", "哔哩", "b站", "bilibili", "bili"], bilibili.get_data),
]
SOURCE_DICT = {}
for names, func in SOURCE_LIST:
  for name in names:
    SOURCE_DICT[name] = (names[0], func)

trending = nonebot.on_command("热搜", aliases={"trending"})
trending.__cmd__ = ["热搜", "trending"]
trending.__brief__ = "看看大家又在撕什么（bushi）"
trending.__doc__ = '''\
/热搜 - 查看支持的来源
/热搜 <来源> - 查看热搜第一页
/热搜 <来源> p<页码> - 查看热搜某一页
/热搜 <来源> <ID> - 查看某一条热搜'''
@trending.handle()
async def handle_trending(msg = CommandArg()):
  args = str(msg).lower().split()
  if len(args) > 2:
    await trending.finish(trending.__doc__)
  elif len(args) == 0:
    segments = []
    for i, _ in SOURCE_LIST:
      seg = i[0]
      if len(i) > 1:
        seg += "（" + "、".join(i[1:]) + "）"
      segments.append(seg)
    await trending.finish("支持的来源：\n" + "\n".join(segments))
  if args[0] not in SOURCE_DICT:
    await trending.finish("不支持的来源")
  src, func = SOURCE_DICT[args[0]]
  now = time.time()
  if src not in STATE.cache or STATE.cache[src].time < now - CONFIG.cache:
    STATE.cache[src] = Cache(time=now, items=await func())
    STATE.dump()
  items = STATE.cache[src].items
  pages = math.ceil(len(items) / CONFIG.page_size)
  page = 1
  if len(args) == 2:
    if not args[1].startswith("p"):
      try: i = int(args[1])
      except: await trending.finish("无效的序号")
      if i < 1 or i > len(items):
        await trending.finish(f"只有 {len(items)} 条热搜")
      item = items[i - 1]
      await trending.finish(MessageSegment.share(item.url, item.title, item.content, item.image))
    else:
      try: page = int(args[1][1:])
      except: await trending.finish("无效的页码")
      if page < 1 or page > pages:
        await trending.finish(f"页码必须在 1 和 {pages} 之间")
  result = []
  begin = (page - 1) * CONFIG.page_size
  for i, v in enumerate(items[begin:begin + CONFIG.page_size], begin + 1):
    result.append(f"{i}: {v.title}")
  result.append(f"第 {page} 页，共 {pages} 页 {len(items)} 条")
  await trending.finish(f"现在的{src}热搜有：\n" + "\n".join(result))
