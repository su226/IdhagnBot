import math
from typing import AsyncGenerator, List, Literal, NoReturn, Type, TypedDict, TypeVar, cast

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, CommandArg
from nonebot.typing import T_State

from util import misc
from util.command import CommandBuilder
from util.help import CategoryItem

from .sources.base import Music, SearchResult
from .sources.bilibili import BilibiliMusic
from .sources.kugou import KugouMusic
from .sources.kuwo import KuwoMusic
from .sources.migu import MiguMusic
from .sources.netease import NeteaseMusic
from .sources.qq_ovooa import QQOvooaMusic

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


SendMode = Literal["share", "link", "voice"]
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
      album = f" - {song.album}" if song.album else ""
      prompt.append(f"{i}: {prefix}{song.name} - {song.artists}{album}")
    prompt.append(f"第 {page + 1} 页，共 {pages} 页，{result.count} 首歌")
    suffix = ""
    if has_vip:
      suffix = "，VIP歌曲只能查看不能播放"
    prompt.append(f"- 发送数字选歌，加上“直链”获取直链，加上“语音”发送语音{suffix}")
    if page < pages:
      prompt.append("- 发送“下”加载下一页")
    prompt.append("- 发送“取”取消点歌")
    return "\n".join(prompt)

  async def finish_with(segment: MessageSegment, mode: SendMode) -> NoReturn:
    if mode == "voice" and (url := segment.data["audio"]):
      file = url
      if headers := segment.data.get("headers", {}):
        http = misc.http()
        async with http.get(url, headers=headers) as response:
          file = await response.read()
      await matcher_t.finish(MessageSegment.record(file))
    if mode in ("link", "voice"):
      desc = f'''
《{segment.data["title"]}》{segment.data["content"]}
详情：{segment.data["url"]}
直链：{segment.data["audio"] or "不可用"}'''
      if segment.data.get("headers", {}):
        desc += " （可能无法直接下载）"
      if download_link := segment.data.get("lossless", None):
        desc += f"\n无损直链：{download_link}"
      await matcher_t.finish(MessageSegment.image(segment.data["image"]) + desc)
    if segment.data["subtype"] == "bilibili":
      # 实际上，go-cqhttp并不认B站，会fallback成QQ音乐
      # 但如果没有subtype参数则会显示为链接而非音乐分享
      # 所以注明一下是B站不是QQ
      segment.data["content"] = f"[哔哩哔哩]{segment.data['content']}"
    await matcher_t.finish(segment)

  async def handle_music(s: T_State, args: Message = CommandArg()):
    keyword = str(args).rstrip()
    if not keyword:
      await matcher_t.finish(matcher_t.__doc__)
    try:
      if keyword.endswith("直链"):
        mode = "link"
        music_id = keyword[:-2].rstrip()
      elif keyword.endswith("语音"):
        mode = "voice"
        music_id = keyword[:-2].rstrip()
      else:
        mode = "share"
        music_id = keyword
      segment = await music_t.from_id(music_id)
      await finish_with(segment, mode)
    except ValueError:
      pass
    state = cast(StateDict, s)
    state["result"] = await music_t.search(keyword, LIMIT)
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
      state["page"] += 1
      await matcher_t.reject(await get_prompt(state))
    if choice.endswith("直链"):
      mode = "link"
      choice = choice[:-2]
    elif choice.endswith("语音"):
      mode = "voice"
      choice = choice[:-2]
    else:
      mode = "share"
    try:
      choice_int = int(choice)
    except ValueError:
      await matcher_t.reject("只能输入数字，请重新输入，或发送“取”取消点歌")
    choices = state["choices"]
    if choice_int < 1 or choice_int > len(choices):
      await matcher_t.reject(f"只能发送 1 和 {len(choices)} 之间的数字，请重新输入，或发送“取”取消点歌")
    await finish_with(await choices[choice_int - 1].segment(), mode)
  matcher_t.got("choice")(got_choice)


append_music_handler(
  CommandBuilder("music.netease", "网易云音乐", "网易云点歌", "网易云", "163")
  .brief("网易云音乐点歌")
  .usage('''\
/网易云音乐 <关键字> - 搜索关键字
/网易云音乐 <id> - 发送指定ID的歌
/网易云音乐 <id> 直链 - 同上，但获取直链
/网易云音乐 <id> 语音 - 同上，但发送语音''')
  .category("music")
  .build(),
  NeteaseMusic
)
append_music_handler(
  CommandBuilder("music.kuwo", "酷我音乐", "酷我点歌", "酷我", "kuwo")
  .brief("酷我音乐点歌")
  .usage('''\
/酷我音乐 <关键字> - 搜索关键字
/酷我音乐 <id> - 发送指定ID的歌
/酷我音乐 <id> 直链 - 同上，但获取直链
/酷我音乐 <id> 语音 - 同上，但发送语音''')
  .category("music")
  .build(),
  KuwoMusic
)
append_music_handler(
  CommandBuilder("music.bilibili", "B站点歌", "b站点歌")
  .brief("B站音频区点歌")
  .usage('''\
/B站点歌 <关键字> - 搜索关键字
/B站点歌 <id> - 发送指定ID的歌
/B站点歌 <id> 直链 - 同上，但获取直链
/B站点歌 <id> 语音 - 同上，但发送语音''')
  .category("music")
  .build(),
  BilibiliMusic
)
append_music_handler(
  CommandBuilder("music.kugou", "酷狗音乐", "酷狗点歌", "酷狗", "kugou")
  .brief("酷狗音乐点歌")
  .usage('''\
/酷狗音乐 <关键字> - 搜索关键字
/酷狗音乐 <id> - 发送指定ID的歌
/酷狗音乐 <id> 直链 - 同上，但获取直链
/酷狗音乐 <id> 语音 - 同上，但发送语音''')
  .category("music")
  .build(),
  KugouMusic
)
append_music_handler(
  CommandBuilder("music.migu", "咪咕音乐", "咪咕点歌", "咪咕", "migu")
  .brief("咪咕音乐点歌")
  .usage('''\
/咪咕音乐 <关键字> - 搜索关键字
/咪咕音乐 <id> - 发送指定ID的歌
/咪咕音乐 <id> 直链 - 同上，但获取直链
/咪咕音乐 <id> 语音 - 同上，但发送语音''')
  .category("music")
  .build(),
  MiguMusic
)
append_music_handler(
  CommandBuilder("music.qq", "QQ音乐", "QQ点歌", "qq音乐", "qq点歌")
  .brief("QQ音乐点歌")
  .usage('''\
/QQ音乐 <关键字> - 搜索关键字
/QQ音乐 <id> - 发送指定ID的歌
/QQ音乐 <id> 直链 - 同上，但获取直链
/QQ音乐 <id> 语音 - 同上，但发送语音
API来自第三方：api.f4team.cn''')
  .category("music")
  .build(),
  QQOvooaMusic
)
category = CategoryItem.find("music")
category.brief = "点歌插件"
category.data.node_str = "music"
