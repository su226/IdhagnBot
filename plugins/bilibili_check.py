import asyncio
import time
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import quote as urlencode

import aiohttp
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, Field

from util import color, command, config_v2, text


class Config(BaseModel):
  cookie: str = ""
  update_interval: int = 86400
  update_timeout: int = 10


class State(BaseModel):
  timestamp: float = 0
  name_cache: dict[int, str] = Field(default_factory=dict)


CONFIG = config_v2.SharedConfig("bilibili_check", Config)
STATE = config_v2.SharedState("bilibili_check", State)

SEARCH_API = "http://api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword={}"
FOLLOW_API = "https://account.bilibili.com/api/member/getCardByMid?mid={}"
MEDAL_API = "https://api.live.bilibili.com/xlive/web-ucenter/user/MedalWall?target_id={}"
VTB_APIS = [
  "https://api.vtbs.moe/v1/short",
  "https://api.tokyo.vtbs.moe/v1/short",
  "https://vtbs.musedash.moe/v1/short",
]
GRADIENT_45DEG_WH = 362.038671968  # 256 * sqrt(2)


async def update_vtbs(http: aiohttp.ClientSession) -> bool:
  async def get_single(url: str):
    async with http.get(url) as resp:
      return await resp.json()
  state = STATE()
  config = CONFIG()
  now = time.time()
  if state.timestamp > now - config.update_interval:
    return True
  done, pending = await asyncio.wait(
    [asyncio.create_task(get_single(api)) for api in VTB_APIS],
    timeout=config.update_timeout, return_when=asyncio.FIRST_COMPLETED)
  for task in pending:
    task.cancel()
  for task in done:
    if task.exception() is None:
      state.name_cache = {x["mid"]: x["uname"] for x in task.result() if x}
      state.timestamp = now
      STATE.dump()
      return True
  return False


@dataclass
class Medal:
  level: int
  name: str
  color_start: int
  color_end: int
  color_border: int


def make_list_item(name: str, uid: int, medal: Medal | None) -> Image.Image:
  name_im = text.render(name, "sans", 32)
  uid_im = text.render(str(uid), "sans", 28)

  padding = 6
  border = 2
  margin = 12
  uid_width = uid_im.width + padding * 2
  im_width = name_im.width + margin + uid_width
  if medal:
    medal_name_layout = text.layout(medal.name, "sans", 28)
    medal_level_layout = text.layout(str(medal.level), "sans", 28)
    medal_width = (
      medal_name_layout.get_pixel_size()[0] + medal_level_layout.get_pixel_size()[0]
      + padding * 4 + border * 2)
    im_width += margin + medal_width
  else:  # 不然静态类型检查器会抱怨
    medal_name_layout = None
    medal_level_layout = None
    medal_width = 0
  im = Image.new("RGBA", (im_width, name_im.height))
  draw = ImageDraw.Draw(im)

  im.paste(name_im, (0, 0), name_im)
  x = name_im.width + margin

  y = (im.height - uid_im.height) // 2
  rounded_im = Image.new("L", (uid_width * 2, uid_im.height * 2), 0)
  ImageDraw.Draw(rounded_im).rounded_rectangle(
    (0, 0, uid_width * 2 - 1, uid_im.height * 2 - 1), 8, 255)
  draw.bitmap(
    (x, y), rounded_im.resize((uid_width, uid_im.height), Image.ANTIALIAS), (221, 221, 221))
  im.paste(uid_im, (x + padding, y), uid_im)
  x += uid_width + margin
  if not medal:
    return im

  medal_name_im = text.render(medal_name_layout, color=(255, 255, 255))
  border_color = color.split_rgb(medal.color_border)
  medal_level_im = text.render(medal_level_layout, color=border_color)

  medal_height = medal_name_im.height + border * 2
  y = (im.height - medal_height) // 2
  draw.rectangle(
    (x, y, x + medal_width - 1, y + medal_height - 1), color.split_rgb(medal.color_border))

  medal_name_bg_width = medal_name_im.width + padding * 2
  ratio = medal_name_bg_width / medal_name_im.height
  gradient = ImageOps.colorize(
    Image.linear_gradient("L"),
    color.split_rgb(medal.color_start),  # type: ignore
    color.split_rgb(medal.color_end)  # type: ignore
  ).rotate(45, Image.BICUBIC, True)
  grad_h = int(GRADIENT_45DEG_WH / (1 + ratio))
  grad_w = int(ratio * grad_h)
  gradient = gradient.crop((
    (gradient.width - grad_w) // 2, (gradient.height - grad_h) // 2,
    (gradient.width + grad_w) // 2, (gradient.height + grad_h) // 2,
  )).resize((medal_name_bg_width, medal_name_im.height), Image.ANTIALIAS)
  im.paste(gradient, (x + border, y + border))
  im.paste(medal_name_im, (x + border + padding, y + border), medal_name_im)

  x += medal_name_bg_width + border
  medal_level_bg_width = medal_level_im.width + padding * 2
  draw.rectangle(
    (x, y + border, x + medal_level_bg_width - 1, y + border + medal_name_im.height - 1),
    (255, 255, 255))
  im.paste(medal_level_im, (x + padding, y + border), medal_level_im)
  return im


def make_header(
  avatar: Image.Image, name: str, uid: int, fans: int, followings: int, vtbs: int
) -> Image.Image:
  ratio = 0 if followings == 0 else vtbs / followings * 100
  name_im = text.render(name, "sans bold", 32)
  uid_im = text.render(str(uid), "sans", 28)
  info_im = text.render(f"<b>粉丝:</b> {fans} <b>关注:</b> {followings}", "sans", 32, markup=True)
  info2_im = text.render(f"<b>VTB:</b> {vtbs} ({ratio:.2f}%)", "sans", 32, markup=True)

  avatar = avatar.convert("RGB").resize((144, 144), Image.ANTIALIAS)
  circle = Image.new("L", (avatar.width * 2, avatar.height * 2), 0)
  ImageDraw.Draw(circle).ellipse((0, 0, circle.width - 1, circle.height - 1), 255)
  avatar.putalpha(circle.resize(avatar.size, Image.ANTIALIAS))

  margin = 12
  padding = 6
  uid_width = uid_im.width + padding * 2
  im = Image.new("RGB", (
    avatar.width + 32 + max(name_im.width + margin + uid_width, info_im.width, info2_im.width),
    max(avatar.height, name_im.height + info_im.height + info2_im.height)
  ), (255, 255, 255))
  im.paste(avatar, (0, 0), avatar)

  x = avatar.width + 32
  im.paste(name_im, (x, 0), name_im)

  y = (name_im.height - uid_im.height) // 2
  rounded_im = Image.new("L", (uid_width * 2, uid_im.height * 2), 0)
  ImageDraw.Draw(rounded_im).rounded_rectangle(
    (0, 0, rounded_im.width - 1, rounded_im.height - 1), 8, 255)
  ImageDraw.Draw(im).bitmap(
    (x + name_im.width + margin, y),
    rounded_im.resize((uid_width, uid_im.height), Image.ANTIALIAS), (221, 221, 221))
  im.paste(uid_im, (x + name_im.width + margin + padding, y), uid_im)

  y = name_im.height
  im.paste(info_im, (x, y), info_im)
  y += info_im.height
  im.paste(info2_im, (x, y), info2_im)
  return im


bilibili_check = (
  command.CommandBuilder("bilibili_check", "查成分")
  .brief("卧槽，□批！")
  .usage("/查成分 <用户名或ID>")
  .build())


@bilibili_check.handle()
async def handle_bilibili_check(arg: Message = CommandArg()):
  name = arg.extract_plain_text().rstrip()
  if not name:
    await bilibili_check.finish("/查成分 <用户名或ID>")
  async with aiohttp.ClientSession() as http:
    if not await update_vtbs(http):
      await bilibili_check.finish("更新VTB数据失败")
    try:
      uid = int(name)
    except ValueError:
      async with http.get(SEARCH_API.format(urlencode(name))) as resp:
        data = await resp.json()
      if "result" not in data.get("data", {}):
        await bilibili_check.finish(f"找不到用户：{name}")
      uid = data["data"]["result"][0]["mid"]
    async with http.get(FOLLOW_API.format(uid)) as resp:
      data = await resp.json()
    async with http.get(data["card"]["face"]) as resp:
      avatar = Image.open(BytesIO(await resp.read()))
    name = data["card"]["name"]
    fans = data["card"]["fans"]
    followings = data["card"]["attentions"]
    names = STATE().name_cache
    vtbs = sorted(
      ((following, names[following]) for following in followings if following in names),
      key=lambda x: x[1])
    medals: dict[str, Medal] = {}
    cookie = CONFIG().cookie
    if cookie:
      async with http.get(MEDAL_API.format(uid), headers={"cookie": cookie}) as resp:
        data = await resp.json()
      for i in data["data"]["list"]:
        info = i["medal_info"]
        medals[info["target_id"]] = Medal(
          info["level"], info["medal_name"],
          info["medal_color_start"], info["medal_color_end"], info["medal_color_border"])
  items = [make_list_item(name, uid, medals.get(uid, None)) for uid, name in vtbs]
  header = make_header(avatar, name, uid, fans, len(followings), len(vtbs))

  if not items:
    items.append(text.render("什么都查不到", "sans", 32))

  margin = 32
  gap = 16
  x_padding = 12
  y_padding = 6
  border = 2
  list_height = sum(im.height + y_padding * 2 for im in items) + border * 2
  im = Image.new("RGB", (
    max(header.width, max(im.width + x_padding * 2 for im in items) + border * 2) + margin * 2,
    header.height + gap + list_height + margin * 2
  ), (255, 255, 255))
  im.paste(header, (margin, margin))
  draw = ImageDraw.Draw(im)

  y = margin + header.height + gap
  draw.rectangle((margin, y, im.width - margin, y + list_height - 1), (238, 238, 238))

  x = margin + 2
  y += 2
  for i, item in enumerate(items):
    item_height = item.height + y_padding * 2
    if i % 2 == 0:
      draw.rectangle((x, y, im.width - margin - border, y + item_height - 1), (255, 255, 255))
    else:
      draw.rectangle((x, y, im.width - margin - border, y + item_height - 1), (247, 247, 247))
    im.paste(item, (x + x_padding, y + y_padding), item)
    y += item_height

  f = BytesIO()
  im.save(f, "PNG")
  await bilibili_check.finish(MessageSegment.image(f))
