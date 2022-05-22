import math
from typing import TypedDict, cast
from urllib.parse import quote

from aiohttp import ClientSession
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State

from util import command

API = "https://music.163.com/api/search/get/web?type=1&offset={offset}&limit={limit}&s={keyword}"
LIMIT = 10


class StateDict(TypedDict):
  keyword: str
  page: int
  end: bool
  choices: list[int]


netease = (
  command.CommandBuilder("netease", "网易云", "netease", "163", "cloudmusic")
  .brief("网易云点歌")
  .usage('''\
/网易云 <关键字> - 搜索关键字
/网易云 <id> - 发送指定ID的歌''')
  .build())


async def get_prompt(state: StateDict):
  if state["end"]:
    return "没有下一页了，请重新输入，或发送“取”取消点歌"
  offset = LIMIT * state["page"]
  async with ClientSession() as http:
    response = await http.get(
      API.format(keyword=quote(state["keyword"]), offset=offset, limit=LIMIT))
    data = await response.json(content_type=None)
  songs = data["result"]["songCount"]
  pages = math.ceil(songs / LIMIT)
  if pages == 0:
    await netease.finish("搜索结果为空")
  prompt = []
  has_vip = False
  for i, song in enumerate(data["result"]["songs"], offset + 1):
    name = song["name"]
    artists = "/".join(x["name"] for x in song["artists"])
    album = song["album"]["name"]
    state["choices"].append(song["id"])
    prefix = ""
    if song["fee"] == 1:
      prefix = "[VIP] "
      has_vip = True
    prompt.append(f"{i}: {prefix}{name} - {artists} - {album}")
  prompt.append(f"第 {state['page'] + 1} 页，共 {pages} 页，{songs} 首歌")
  suffix = ""
  if has_vip:
    suffix = "，VIP歌曲只能查看不能播放"
  prompt.append(f"- 发送数字选歌{suffix}")
  state["page"] += 1
  if state["page"] < pages:
    prompt.append("- 发送“下”加载下一页")
  else:
    state["end"] = True
  prompt.append("- 发送“取”取消点歌")
  return "\n".join(prompt)


@netease.handle()
async def handle_netease(state: T_State, args: Message = CommandArg()):
  keyword = str(args).rstrip()
  if not keyword:
    await netease.finish(netease.__doc__)
  try:
    song_id = int(keyword)
  except ValueError:
    pass
  else:
    await netease.finish(MessageSegment.music("163", song_id))
  state["keyword"] = keyword
  state["page"] = 0
  state["end"] = False
  state["choices"] = []
  await netease.send(await get_prompt(cast(StateDict, state)))


@netease.got("choice")
async def receive_netease(state: T_State, choice: str = ArgStr()):
  choice = choice.strip()
  if choice == "取":
    await netease.finish("点歌取消")
  elif choice == "下":
    await netease.reject(await get_prompt(cast(StateDict, state)))
  try:
    choice_int = int(choice)
  except ValueError:
    await netease.reject("只能输入数字，请重新输入，或发送“取”取消点歌")
  choices = state["choices"]
  if choice_int < 1 or choice_int > len(choices):
    await netease.reject(f"只能发送 1 和 {len(choices)} 之间的数字，请重新输入，或发送“取”取消点歌")
  await netease.finish(MessageSegment.music("163", choices[choice_int - 1]))
