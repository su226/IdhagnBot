from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError
from typing import Awaitable, Callable
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
import base64
import nonebot

FactoryType = Callable[[], Awaitable[str]]
def simple(url: str) -> FactoryType:
  async def func() -> str:
    try:
      async with ClientSession() as http:
        response = await http.get(url)
        data = await response.read()
    except ClientConnectionError:
      return "网络错误"
    return f"[CQ:image,file=base64://{base64.b64encode(data).decode()}]"
  return func

SOURCES: list[tuple[FactoryType, str, list[str]]] = [
  (simple("https://thiscatdoesnotexist.com/"), "猫", ["cat", "c"]),
  (simple("https://thisartworkdoesnotexist.com/"), "画作", ["artwork", "a"]),
  (simple("https://thishorsedoesnotexist.com/"), "马", ["horse", "h"]),
  (simple("https://thispersondoesnotexist.com/image"), "人", ["person", "p"]),
  (simple("https://thisrentaldoesnotexist.com/img-new/hero.jpg"), "房产", ["rental", "r"]),
]
SOURCES_DICT: dict[str, FactoryType] = {}
for func, _, ids in SOURCES:
  for id in ids:
    SOURCES_DICT[id] = func

txdne = nonebot.on_command("txdne")
txdne.__cmd__ = "txdne"
txdne.__brief__ = "This X Does Not Exist"
txdne.__doc__ = '''\
/txdne - 查看支持的来源
/txdne <来源ID> - 随机图片'''
@txdne.handle()
async def handle_txdne(args: Message = CommandArg()):
  site = args.extract_plain_text().rstrip()
  if site in SOURCES_DICT:
    result = await SOURCES_DICT[site]()
    await txdne.finish(Message(result))
  segments = []
  if site:
    segments.append(f"未知的来源：{site}")
  segments.append("所有支持的来源：")
  for _, name, ids in SOURCES:
    segments.append(f"{name} - {'、'.join(ids)}")
  await txdne.finish("\n".join(segments))
