import math
import time
from typing import Dict, List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from pydantic import BaseModel, Field

from util import command, configs

from . import baidu, bilibili, cctv, weibo, zhihu
from .common import Item


class Config(BaseModel):
  cache: int = 600
  page_size: int = 10


class Cache(BaseModel):
  time: float = 0
  items: List[Item] = Field(default_factory=list)


class State(BaseModel):
  cache: Dict[str, Cache] = Field(default_factory=dict)


CONFIG = configs.SharedConfig("trending", Config)
STATE = configs.SharedState("trending", State)
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

trending = (
  command.CommandBuilder("trending", "热搜", "trending")
  .brief("看看大家又在撕什么（bushi）")
  .usage('''\
/热搜 - 查看支持的来源
/热搜 <来源> - 查看热搜第一页
/热搜 <来源> p<页码> - 查看热搜某一页
/热搜 <来源> <ID> - 查看某一条热搜''')
  .build())


@trending.handle()
async def handle_trending(msg: Message = CommandArg()):
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
  config = CONFIG()
  state = STATE()
  if src not in state.cache or state.cache[src].time < now - config.cache:
    state.cache[src] = Cache(time=now, items=await func())
    STATE.dump()
  items = state.cache[src].items
  pages = math.ceil(len(items) / config.page_size)
  page = 1
  if len(args) == 2:
    if not args[1].startswith("p"):
      try:
        i = int(args[1])
      except ValueError:
        await trending.finish("无效的序号")
      if i < 1 or i > len(items):
        await trending.finish(f"只有 {len(items)} 条热搜")
      item = items[i - 1]
      await trending.finish(MessageSegment.share(item.url, item.title, item.content, item.image))
    else:
      try:
        page = int(args[1][1:])
      except ValueError:
        await trending.finish("无效的页码")
      if page < 1 or page > pages:
        await trending.finish(f"页码必须在 1 和 {pages} 之间")
  result = []
  begin = (page - 1) * config.page_size
  for i, v in enumerate(items[begin:begin + config.page_size], begin + 1):
    result.append(f"{i}: {v.title}")
  result.append(f"第 {page} 页，共 {pages} 页 {len(items)} 条")
  await trending.finish(f"现在的{src}热搜有：\n" + "\n".join(result))
