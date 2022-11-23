from typing import Awaitable, Callable, Dict, List, Tuple

import aiohttp
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command, misc

FactoryType = Callable[[], Awaitable[MessageSegment]]


def simple(url: str) -> FactoryType:
  async def func() -> MessageSegment:
    http = misc.http()
    try:
      async with http.get(url) as response:
        return MessageSegment.image(await response.read())
    except aiohttp.ClientError:
      return MessageSegment.text("网络错误")
  return func


SOURCES: List[Tuple[FactoryType, str, List[str]]] = [
  (simple("https://thiscatdoesnotexist.com/"), "猫", ["cat", "c"]),
  (simple("https://thisartworkdoesnotexist.com/"), "画作", ["artwork", "a"]),
  (simple("https://thishorsedoesnotexist.com/"), "马", ["horse", "h"]),
  (simple("https://thispersondoesnotexist.com/image"), "人", ["person", "p"]),
  (simple("https://thisrentaldoesnotexist.com/img-new/hero.jpg"), "房产", ["rental", "r"]),
]
SOURCES_DICT: Dict[str, FactoryType] = {}
for func, _, ids in SOURCES:
  for id in ids:
    SOURCES_DICT[id] = func

txdne = (
  command.CommandBuilder("txdne", "txdne")
  .brief("This X Does Not Exist")
  .usage('''\
/txdne - 查看支持的来源
/txdne <来源ID> - 随机图片''')
  .build())


@txdne.handle()
async def handle_txdne(args: Message = CommandArg()):
  site = args.extract_plain_text().rstrip()
  if site in SOURCES_DICT:
    result = await SOURCES_DICT[site]()
    await txdne.finish(result)
  segments = []
  if site:
    segments.append(f"未知的来源：{site}")
  segments.append("所有支持的来源：")
  for _, name, ids in SOURCES:
    segments.append(f"{name} - {'、'.join(ids)}")
  await txdne.finish("\n".join(segments))
