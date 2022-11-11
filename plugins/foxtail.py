import base64
import re
import time
from collections import defaultdict
from typing import Literal
from urllib.parse import quote as urlencode

import aiohttp
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import Arg, ArgPlainText, CommandArg, EventMessage
from nonebot.typing import T_State
from pydantic import BaseModel

from util import command, configs, help, misc
from util.api_common import furbot


class Config(BaseModel):
  keyword: str = "来只兽"
CONFIG = configs.SharedConfig("foxtail", Config)


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


async def send_pic(bot: Bot, event: Event, data: dict) -> None:
  http = misc.http()
  status = int(data["examine"])
  if status == 1:
    async with http.get(DOWNLOAD_API.format(data["picture"], 0)) as response:
      image_data = await response.json()
      image_segment = MessageSegment.image(image_data["url"])
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
  @staticmethod
  def name() -> str:
    return "兽云祭"

  @staticmethod
  def keyword() -> str:
    return CONFIG().keyword

  @staticmethod
  def available() -> bool:
    return True

  @staticmethod
  async def handle(bot: Bot, event: Event, args: str) -> None:
    http = misc.http()
    if match := UID_RE.fullmatch(args):
      async with http.get(INFO_API.format(match[0], 0)) as response:
        data = await response.json()
      if "picture" in data:
        await send_pic(bot, event, data["picture"][0])
      else:
        await bot.send(event, f"{HEADER}\n{data['msg']}")
      return
    try:
      fid = int(args)
    except ValueError:
      pass
    else:
      async with http.get(INFO_API.format(fid, 1)) as response:
        data = await response.json()
      if "picture" in data:
        await send_pic(bot, event, data["picture"][0])
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

    url = RANDOM_API.format(urlencode(name), type)
    async with http.get(url) as response:
      data = await response.json()
      data = data["picture"]

    if "picture" not in data:
      if type:
        await bot.send(
          event, f"{HEADER}\n这只兽似乎不存在，或者没有指定类型的图片，目前 IdhagnBot 暂不支持投稿。"
        )
      else:
        await bot.send(event, f"{HEADER}\n这只兽似乎不存在，目前 IdhagnBot 暂不支持投稿。")
      return

    await send_pic(bot, event, data)
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
keyword = nonebot.on_message(keyword_rule, picture.permission, block=True)
@keyword.handle()
async def handle_regex(bot: Bot, event: Event, message: Message = EventMessage()):
  config = CONFIG()
  args = message.extract_plain_text().lstrip().removeprefix(config.keyword)
  await Source.handle(bot, event, args.strip())


search = (
  command.CommandBuilder("foxtail.search", "兽云祭搜索")
  .category("foxtail")
  .brief("搜索兽图")
  .usage("/兽云祭搜索 <名字> - 搜索兽图")
  .build()
)
@search.handle()
async def handle_search(message: Message = CommandArg()) -> None:
  name = message.extract_plain_text().rstrip()
  if not name:
    await search.finish(search.__doc__)
  http = misc.http()
  async with await http.get(SEARCH_API.format(name)) as response:
    data = await response.json()
  result: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
  for i in data["open"]:
    result[i["name"]][i["type"]].append(i["id"])
  segments: list[str] = []
  for name, pics in result.items():
    lines: list[str] = []
    lines.append(name)
    for type, ids in pics.items():
      lines.append(TYPE_TO_STR[int(type)] + "：" + "、".join(ids))
    segments.append("\n".join(lines))
  await search.finish(HEADER + "\n" + "\n----------------\n".join(segments))


class SubmitData(BaseModel):
  name: str
  type: Literal[0, 1, 2]
  desc: str
  note: str


submit = (
  command.CommandBuilder("foxtail.submit", "兽云祭投稿")
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
async def got_confirm(state: T_State, confirm: str = ArgPlainText()) -> None:
  if confirm != "是":
    await submit.finish("投稿取消")
  data: SubmitData = state["data"]
  image: str = state["image"]
  http = misc.http()
  async with http.get(image) as response:
    image_data = await response.read()
  form = aiohttp.FormData({
    "name": data.name,
    "type": data.type,
    "suggest": data.desc,
    "rem": data.note,
  })
  form.add_field("file", image_data)
  async with http.post("https://cloud.foxtail.cn/api/function/upload", data=form) as response:
    result = await response.json()
  if result["code"] != 200:
    await submit.finish(HEADER + "\n提交失败: " + result["msg"])
  await submit.finish(HEADER + f'''
提交成功，图片正在审核中。
SID: {result["id"]}
UID: {result["picture"]}''')


info = (
  command.CommandBuilder("foxtail.info", "兽云祭信息")
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
公开图片数：{data['page']['count']}
待审核图片数: {data['examine']['count']}
运行时长: {data['time']['count']}天''')


furbot.register_universal_keyword()
category = help.CategoryItem.find("foxtail")
category.brief = "兽云祭"
