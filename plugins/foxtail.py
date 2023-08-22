import base64
import itertools
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Literal, Tuple
from urllib.parse import quote as encodeuri

import aiohttp
import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageEvent, MessageSegment
from nonebot.exception import ActionFailed
from nonebot.params import Arg, ArgPlainText, CommandArg, EventMessage
from nonebot.typing import T_State
from pydantic import BaseModel

from util import command, configs, context, help, misc, permission
from util.api_common import furbot


@dataclass
class SearchResult:
  processing: List[str] = field(default_factory=list)
  accepted: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
  rejected: List[str] = field(default_factory=list)

  def __len__(self) -> int:
    accepted_len = sum(len(x) for x in self.accepted.values())
    return len(self.processing) + len(self.rejected) + accepted_len

  def __lt__(self, other: "SearchResult") -> bool:
    return len(self) < len(other)


class Config(BaseModel):
  keyword: str = "来只兽"
  show_private: bool = True
  user: str = ""
  password: str = ""
  token: str = ""

  @property
  def can_login(self) -> bool:
    return bool(self.user and self.password and self.token)


class State(BaseModel):
  cookies: str = ""

  @property
  def headers(self) -> Dict[str, str]:
    return {"Cookie": self.cookies}


CONFIG = configs.SharedConfig("foxtail", Config)
STATE = configs.SharedState("foxtail", State)
RANDOM_API = "https://cloud.foxtail.cn/api/function/random?name={}&type={}"
INFO_API = "https://cloud.foxtail.cn/api/function/pullpic?picture={}&model={}"
DOWNLOAD_API = "https://cloud.foxtail.cn/api/function/pictures?picture={}&model={}"
SEARCH_API = "https://cloud.foxtail.cn/api/function/pulllist?name={}"
SUBMIT_GUI_URL = "https://idhagnbot.su226.tk/docs/misc/foxtail-submit"
UID_RE = re.compile(r"([A-Za-z0-9]{5}-){3}[A-Za-z0-9]{5}")
STR_TO_TYPE = {
  "设定": 0,
  "毛图": 1,
  "插画": 2,
  "0": 0,
  "1": 1,
  "2": 2,
}
TYPE_TO_STR = {
  0: "设定",
  1: "毛图",
  2: "插画",
}
HEADER = "======== 兽云祭 ========"
USAGE_TYPES = "类型包括：设定(0)、毛图(1)、插画(2)"
USAGE_BASE = f'''\
/兽云祭 [名字] [类型] - 发送随机兽图，名字和类型都可省略
/兽云祭 <图片SID或UID> - 发送指定兽图（或查询审核状态）
内容来自兽云祭 API，官网：furbot.cn
{USAGE_TYPES}'''
USAGE_KEYWORD = "也可以使用关键词“{}”触发"


async def ensure_login() -> SimpleCookie[str]:
  config = CONFIG()
  if not config.can_login:
    return SimpleCookie()
  state = STATE()
  http = misc.http()
  if state.cookies:
    cookies = SimpleCookie(state.cookies)
    async with http.get("https://cloud.foxtail.cn/api/account/state", cookies=cookies) as response:
      res = await response.json()
    if res["code"] == "11100":
      return cookies
  logger.info("兽云祭帐号登录过期，重新登录中")
  async with http.post("https://cloud.foxtail.cn/api/account/login", data={
    "account": config.user,
    "password": config.password,
    "model": 1,
    "token": config.token,
  }) as response:
    res = await response.json()
  if res["code"] == "10000":
    state.cookies = response.cookies.output([], "", ";")[1:]  # 移除开头的空格
  else:
    logger.error(f"兽云祭帐号登录失败: {res}")
    state.cookies = ""
  STATE.dump()
  return response.cookies


async def send_pic(
  bot: Bot, event: Event, data: Dict[str, Any], cookies: SimpleCookie[str]
) -> None:
  status = int(data.get("examine", 1))  # 随机接口没有审核参数
  if status == 1:
    http = misc.http()
    async with http.get(DOWNLOAD_API.format(data["picture"], 0), cookies=cookies) as response:
      image_data = await response.json()
    code = image_data["code"]
    if code == "20600":
      image_segment = MessageSegment.image(image_data["url"])
    elif code in {"20602", "20603"}:
      image_segment = MessageSegment.text("没有查看权限")
    else:
      image_segment = MessageSegment.text(image_data["msg"])
  elif status == 2:
    image_segment = MessageSegment.text("图片未过审")
  else:
    image_segment = MessageSegment.text("图片正在审核")
  stime = time.gmtime(int(data["timestamp"]))
  upload_time = time.strftime("%Y-%m-%d %H:%M:%S", stime)
  if (content := data["suggest"]):
    comment = f"\n备注: {content}"
  else:
    comment = ""
  type_int = int(data["type"])
  type_str = TYPE_TO_STR[type_int]
  header = f'''\
{HEADER}
名字: {data["name"]}{comment}
SID: {data["id"]}
UID: {data["picture"]}
类型: {type_str}({type_int})
上传于: {upload_time}
点赞: {data["thumbs"]}
收藏: {data["Collection"]}
'''
  await bot.send(event, header + image_segment)


class Source:
  name = "兽云祭"
  node: Tuple[str, ...] = ("foxtail", "picture", "keyword")

  @staticmethod
  def keyword() -> str:
    return CONFIG().keyword

  @staticmethod
  def available() -> bool:
    return True

  @staticmethod
  async def handle(bot: Bot, event: Event, args: str) -> None:
    config = CONFIG()
    cookies = await ensure_login() if config.show_private else SimpleCookie()
    http = misc.http()
    if match := UID_RE.fullmatch(args):
      async with http.get(INFO_API.format(match[0], 0), cookies=cookies) as response:
        data = await response.json()
      if "picture" in data:
        await send_pic(bot, event, data["picture"][0], cookies)
      else:
        await bot.send(event, f"{HEADER}\n{data['msg']}")
      return
    try:
      fid = int(args)
    except ValueError:
      pass
    else:
      async with http.get(INFO_API.format(fid, 1), cookies=cookies) as response:
        data = await response.json()
      if "picture" in data:
        await send_pic(bot, event, data["picture"][0], cookies)
      else:
        await bot.send(event, f"{HEADER}\n{data['msg']}")
      return

    argv = args.split()
    if len(argv) == 0:
      name = ""
      type = ""
    elif len(argv) == 1:
      if argv[0] in STR_TO_TYPE:
        name = ""
        type = STR_TO_TYPE[argv[0]]
      else:
        name = argv[0]
        type = ""
    elif len(argv) == 2:
      if argv[1] not in STR_TO_TYPE:
        await bot.send(event, f"未知类型：{argv[1]}\n{USAGE_TYPES}")
        return
      name = argv[0]
      type = STR_TO_TYPE[argv[1]]
    else:
      await bot.send(event, picture_usage() or "")
      return

    url = RANDOM_API.format(encodeuri(name), type)
    async with http.get(url, cookies=cookies) as response:
      data = await response.json()
      data = data["picture"]

    if "picture" not in data:
      if type:
        await bot.send(
          event, f"{HEADER}\n这只兽似乎不存在，或者没有指定类型的图片。"
        )
      else:
        await bot.send(event, f"{HEADER}\n这只兽似乎不存在。")
      return

    await send_pic(bot, event, data, cookies)
furbot.universal_sources["foxtail"] = Source


def picture_usage() -> str:
  config = CONFIG()
  usage = USAGE_BASE
  if config.keyword:
    usage += "\n" + USAGE_KEYWORD.format(config.keyword)
  return usage
picture = (
  command.CommandBuilder("foxtail.picture", "兽云祭")
  .category("foxtail")
  .brief("使用兽云祭API的随机兽图")
  .usage(picture_usage)
  .build()
)
@picture.handle()
async def handle_picture(bot: Bot, event: Event, message: Message = CommandArg()):
  await Source.handle(bot, event, message.extract_plain_text().rstrip())


async def keyword_rule(message: Message = EventMessage()) -> bool:
  config = CONFIG()
  if not config.keyword:
    return False
  seg = message[0]
  return seg.is_text() and str(seg).lstrip().startswith(config.keyword)
keyword = nonebot.on_message(
  keyword_rule,
  context.build_permission(Source.node, permission.Level.MEMBER),
  block=True
)
@keyword.handle()
async def handle_regex(bot: Bot, event: Event, message: Message = EventMessage()):
  config = CONFIG()
  args = misc.removeprefix(message.extract_plain_text().lstrip(), config.keyword)
  await Source.handle(bot, event, args.strip())


search = (
  command.CommandBuilder("foxtail.search", "兽云祭搜索")
  .category("foxtail")
  .brief("搜索兽图")
  .usage('''\
/兽云祭搜索 <名字> - 搜索兽图
/兽云祭搜索 <名字> 全部 - 包括未过审的ID''')
  .build()
)
@search.handle()
async def handle_search(bot: Bot, event: Event, message: Message = CommandArg()) -> None:
  name = message.extract_plain_text().rstrip()
  show_all = name.endswith("全部")
  name = misc.removesuffix(name, "全部").rstrip()
  if not name:
    await search.finish(search.__doc__)
  config = CONFIG()
  cookies = await ensure_login() if config.show_private else {}
  http = misc.http()
  async with await http.get(SEARCH_API.format(encodeuri(name)), cookies=cookies) as response:
    data = await response.json()

  result: Dict[str, SearchResult] = defaultdict(SearchResult)
  for i in itertools.chain(data["open"], data["private"], data["given"]):
    if i["examine"] == "0":
      result[i["name"]].processing.append(i["id"])
    elif i["examine"] == "1":
      result[i["name"]].accepted[i["type"]].append(i["id"])
    else:
      result[i["name"]].rejected.append(i["id"])
  sorted_result = sorted(result.items(), key=lambda x: x[1], reverse=True)

  segments: List[str] = []
  for name, pics in sorted_result:
    lines: List[str] = []
    lines.append(f"「{name}」")
    if pics.processing:
      lines.append("审核中：" + "、".join(pics.processing))
    for type, ids in pics.accepted.items():
      lines.append(TYPE_TO_STR[int(type)] + "：" + "、".join(ids))
    if pics.rejected and show_all:
      lines.append("未过审：" + "、".join(pics.rejected))
    if len(lines) > 1:
      segments.append("\n".join(lines))

  if len(segments) > 5:
    bot_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = [misc.forward_node(event.self_id, bot_name, HEADER)]
    nodes.extend([misc.forward_node(event.self_id, bot_name, i) for i in segments])
    try:
      await misc.send_forward_msg(bot, event, *nodes)
      await search.finish()
    except ActionFailed:
      pass
    segments = segments[:5] + ["结果太多，这里贴不下……"]
  elif not segments:
    segments = ["什么都没搜到……"]
  await search.finish(HEADER + "\n" + "\n----------------\n".join(segments))


class SubmitData(BaseModel):
  name: str
  type: Literal[0, 1, 2]
  desc: str
  note: str


submit = (
  command.CommandBuilder("foxtail.submit", "兽云祭投稿", "兽云祭上传")
  .rule(lambda: bool(CONFIG().can_login))
  .help_condition(lambda _: bool(CONFIG().can_login))
  .category("foxtail")
  .brief("投稿兽图")
  .usage(f'''\
/兽云祭投稿 <投稿数据>
请在此处生成投稿命令：{SUBMIT_GUI_URL}''')
  .build()
)
@submit.handle()
async def handle_submit(state: T_State, arg: Message = CommandArg()) -> None:
  text = arg.extract_plain_text().rstrip()
  if not text:
    await submit.finish(f"请在此处生成投稿命令：{SUBMIT_GUI_URL}")
  try:
    raw = base64.b64decode(text)
    data = SubmitData.parse_raw(raw)
  except ValueError:
    await submit.finish(f"无效投稿命令，请重新生成：{SUBMIT_GUI_URL}")
  state["data"] = data
  await submit.send("请发送要投稿的图片，发送不是图片的内容将取消投稿")

@submit.got("image")
async def got_image(state: T_State, image: Message = Arg()) -> None:
  seg = image[0]
  if len(image) != 1 or seg.type != "image":
    await submit.finish("发送的内容不是图片，投稿取消")
  state["image"] = seg.data["url"]
  data: SubmitData = state["data"]
  await submit.send(f'''\
确认内容无误并投稿？
发送“是”确认投稿，发送其他内容取消投稿。
名字：{data.name}
类型：{TYPE_TO_STR[data.type]}({data.type})
备注：{data.desc or "(无备注)"}
审核留言：{data.note or "(无留言)"}
图片：
''' + image)

@submit.got("confirm")
async def got_confirm(event: MessageEvent, state: T_State, confirm: str = ArgPlainText()) -> None:
  if confirm != "是":
    await submit.finish("投稿取消")
  data: SubmitData = state["data"]
  image: str = state["image"]
  http = misc.http()
  async with http.get(image) as response:
    image_data = await response.read()
  note = f"[IdhagnBot]投稿用户: {event.user_id}\n" + data.note
  form = aiohttp.FormData({
    "name": data.name,
    "type": str(data.type),
    "suggest": data.desc,
    "rem": note,
  })
  form.add_field("file", image_data)
  async with http.post(
    "https://cloud.foxtail.cn/api/function/upload", data=form, headers=await ensure_login()
  ) as response:
    result = await response.json()
  if result["code"] != "20000":
    await submit.finish(HEADER + "\n提交失败: " + result["msg"])
  await submit.finish(HEADER + f'''
提交成功，图片正在审核中。
SID: {result["id"]}
UID: {result["picture"]}''')


info = (
  command.CommandBuilder("foxtail.info", "兽云祭信息", "兽云祭状态")
  .category("foxtail")
  .brief("兽云祭服务器信息")
  .build()
)
@info.handle()
async def handle_info() -> None:
  http = misc.http()
  async with http.get("https://cloud.foxtail.cn/api/information/feedback") as response:
    data = await response.json()
  await info.finish(f'''\
{HEADER}
主页访问次数：{data['page']['count']}
图片查看次数：{data['total']['count']}
图片总数：{data['atlas']['count']}
公开图片数：{data['power']['count']}
待审核图片数: {data['examine']['count']}
运行时长: {data['time']['count']}天''')


furbot.register_universal_keyword()
category = help.CategoryItem.find("foxtail")
category.data.node_str = "foxtail"
category.brief = "兽云祭"
del category
