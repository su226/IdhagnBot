import math
from typing import AsyncGenerator, List, Type, TypedDict, TypeVar, cast

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State

from util.command import CommandBuilder

from .sources.base import Music, SearchResult
from .sources.netease import NeteaseMusic

API = "https://music.163.com/api/search/get/web?type=1&offset={offset}&limit={limit}&s={keyword}"
LIMIT = 10


class StateDict(TypedDict):
  result: SearchResult[Music]
  page: int
  choices: List[Music]


T = TypeVar("T")
async def pull(gen: AsyncGenerator[T, None], limit: int) -> List[T]:
  result = []
  for _ in range(limit):
    try:
      value = await gen.__anext__()
    except StopAsyncIteration:
      break
    result.append(value)
  return result


def append_music_handler(matcher_t: Type[Matcher], music_t: Type[Music]) -> None:
  async def get_prompt(state: StateDict):
    pages = math.ceil(state["result"].count / LIMIT)
    if pages == 0:
      await matcher_t.finish("搜索结果为空")
    page = state["page"]
    if page >= pages:
      return "没有下一页了，请重新输入，或发送“取”取消点歌"
    result = state["result"]
    songs = await pull(result.musics, LIMIT)
    state["choices"].extend(songs)
    prompt = []
    has_vip = False
    for i, song in enumerate(songs, page * LIMIT + 1):
      prefix = ""
      if song.vip:
        prefix = "[VIP] "
        has_vip = True
      prompt.append(f"{i}: {prefix}{song.name} - {song.artists} - {song.album}")
    prompt.append(f"第 {page + 1} 页，共 {pages} 页，{result.count} 首歌")
    suffix = ""
    if has_vip:
      suffix = "，VIP歌曲只能查看不能播放"
    prompt.append(f"- 发送数字选歌{suffix}")
    if page < pages:
      prompt.append("- 发送“下”加载下一页")
    prompt.append("- 发送“取”取消点歌")
    return "\n".join(prompt)

  async def handle_music(s: T_State, args: Message = CommandArg()):
    keyword = str(args).rstrip()
    if not keyword:
      await matcher_t.finish(matcher_t.__doc__)
    try:
      song_id = int(keyword)
    except ValueError:
      pass
    else:
      await matcher_t.finish(MessageSegment.music("163", song_id))
    state = cast(StateDict, s)
    state["result"] = await music_t.search(keyword)
    state["page"] = 0
    state["choices"] = []
    await matcher_t.send(await get_prompt(state))
  matcher_t.handle()(handle_music)

  async def got_choice(s: T_State, choice: str = ArgStr()):
    state = cast(StateDict, s)
    choice = choice.strip()
    if choice == "取":
      await matcher_t.finish("点歌取消")
    elif choice == "下":
      await matcher_t.reject(await get_prompt(state))
    try:
      choice_int = int(choice)
    except ValueError:
      await matcher_t.reject("只能输入数字，请重新输入，或发送“取”取消点歌")
    choices = state["choices"]
    if choice_int < 1 or choice_int > len(choices):
      await matcher_t.reject(f"只能发送 1 和 {len(choices)} 之间的数字，请重新输入，或发送“取”取消点歌")
    await matcher_t.finish(choices[choice_int - 1].segment())
  matcher_t.got("choice")(got_choice)


netease = (
  CommandBuilder("music.netease", "网易云", "netease", "163", "cloudmusic")
  .brief("网易云点歌")
  .usage('''\
/网易云 <关键字> - 搜索关键字
/网易云 <id> - 发送指定ID的歌''')
  .build()
)
append_music_handler(netease, NeteaseMusic)
