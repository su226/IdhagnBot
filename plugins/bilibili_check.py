import asyncio
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import quote as encodeuri

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, Field, SecretStr

from util import colorutil, command, configs, imutil, misc, textutil


class Config(BaseModel):
  cookie: SecretStr = SecretStr("")
  update_interval: int = 86400
  update_timeout: int = 10


class State(BaseModel):
  timestamp: float = 0
  name_cache: Dict[int, str] = Field(default_factory=dict)


CONFIG = configs.SharedConfig("bilibili_check", Config)
STATE = configs.SharedState("bilibili_check", State)

SEARCH_API = "http://api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword={}"
FOLLOW_API = "https://account.bilibili.com/api/member/getCardByMid?mid={}"
MEDAL_API = "https://api.live.bilibili.com/xlive/web-ucenter/user/MedalWall?target_id={}"
VTB_APIS = [
  "https://api.vtbs.moe/v1/short",
  "https://api.tokyo.vtbs.moe/v1/short",
  "https://vtbs.musedash.moe/v1/short",
]
GRADIENT_45DEG_WH = 362.038671968  # 256 * sqrt(2)


async def update_vtbs() -> bool:
  async def get_single(url: str):
    async with http.get(url) as resp:
      return await resp.json()
  state = STATE()
  config = CONFIG()
  http = misc.http()
  now = time.time()
  if state.timestamp > now - config.update_interval:
    return True
  done, pending = await asyncio.wait(
    [asyncio.create_task(get_single(api)) for api in VTB_APIS],
    timeout=config.update_timeout, return_when=asyncio.FIRST_COMPLETED
  )
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


def make_list_item(name: str, uid: int, medal: Optional[Medal]) -> Image.Image:
  name_im = textutil.render(name, "sans", 32)
  uid_im = textutil.render(str(uid), "sans", 28)

  padding = 6
  border = 2
  margin = 12
  uid_width = uid_im.width + padding * 2
  im_width = name_im.width + margin + uid_width
  _bound: Any = None  # HACK
  medal_name_layout = _bound
  medal_level_layout = _bound
  medal_width = _bound
  if medal:
    medal_name_layout = textutil.layout(medal.name, "sans", 28)
    medal_level_layout = textutil.layout(str(medal.level), "sans", 28)
    medal_width = (
      medal_name_layout.get_pixel_size()[0] + medal_level_layout.get_pixel_size()[0]
      + padding * 4 + border * 2
    )
    im_width += margin + medal_width
  im = Image.new("RGBA", (im_width, name_im.height))

  im.paste(name_im, (0, 0), name_im)
  x = name_im.width + margin

  y = (im.height - uid_im.height) // 2
  rounded_im = Image.new("L", (uid_width * 2, uid_im.height * 2), 0)
  ImageDraw.Draw(rounded_im).rounded_rectangle(
    (0, 0, uid_width * 2 - 1, uid_im.height * 2 - 1), 8, 255
  )
  rounded_im = rounded_im.resize((uid_width, uid_im.height), imutil.scale_resample())
  im.paste((221, 221, 221), (x, y), rounded_im)
  im.paste(uid_im, (x + padding, y), uid_im)
  x += uid_width + margin
  if not medal:
    return im

  medal_name_im = textutil.render(medal_name_layout, color=(255, 255, 255))
  border_color = colorutil.split_rgb(medal.color_border)
  medal_level_im = textutil.render(medal_level_layout, color=border_color)

  medal_height = medal_name_im.height + border * 2
  y = (im.height - medal_height) // 2
  im.paste(colorutil.split_rgb(medal.color_border), (x, y, x + medal_width, y + medal_height))

  medal_name_bg_width = medal_name_im.width + padding * 2
  ratio = medal_name_bg_width / medal_name_im.height
  gradient = ImageOps.colorize(
    Image.linear_gradient("L"),
    colorutil.split_rgb(medal.color_start),  # type: ignore
    colorutil.split_rgb(medal.color_end)  # type: ignore
  ).rotate(45, imutil.resample(), True)
  grad_h = int(GRADIENT_45DEG_WH / (1 + ratio))
  grad_w = int(ratio * grad_h)
  gradient = gradient.crop((
    (gradient.width - grad_w) // 2, (gradient.height - grad_h) // 2,
    (gradient.width + grad_w) // 2, (gradient.height + grad_h) // 2,
  )).resize((medal_name_bg_width, medal_name_im.height), imutil.scale_resample())
  im.paste(gradient, (x + border, y + border))
  im.paste(medal_name_im, (x + border + padding, y + border), medal_name_im)

  x += medal_name_bg_width + border
  medal_level_bg_width = medal_level_im.width + padding * 2
  im.paste(
    (255, 255, 255),
    (x, y + border, x + medal_level_bg_width, y + border + medal_name_im.height)
  )
  im.paste(medal_level_im, (x + padding, y + border), medal_level_im)
  return im


def make_header(
  avatar: Image.Image, name: str, uid: int, fans: int, followings: int, vtbs: int
) -> Image.Image:
  ratio = 0 if followings == 0 else vtbs / followings * 100
  name_im = textutil.render(name, "sans bold", 32)
  uid_im = textutil.render(str(uid), "sans", 28)
  info_im = textutil.render(f"<b>粉丝:</b> {fans} <b>关注:</b> {followings}", "sans", 32, markup=True)
  info2_im = textutil.render(f"<b>VTB:</b> {vtbs} ({ratio:.2f}%)", "sans", 32, markup=True)

  avatar = avatar.convert("RGB").resize((144, 144), imutil.scale_resample())
  imutil.circle(avatar)

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
    (0, 0, rounded_im.width - 1, rounded_im.height - 1), 8, 255
  )
  rounded_im = rounded_im.resize((uid_width, uid_im.height), imutil.scale_resample())
  im.paste((221, 221, 221), (x + name_im.width + margin, y), rounded_im)
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
  .rule(lambda: bool(CONFIG().cookie))
  .help_condition(lambda _: bool(CONFIG().cookie))
  .build()
)
@bilibili_check.handle()
async def handle_bilibili_check(arg: Message = CommandArg()):
  name = arg.extract_plain_text().rstrip()
  if not name:
    await bilibili_check.finish("/查成分 <用户名或ID>")
  if not await update_vtbs():
    await bilibili_check.finish("更新VTB数据失败")
  headers = {"Cookie": CONFIG().cookie.get_secret_value()}
  http = misc.http()
  try:
    uid = int(name)
  except ValueError:
    async with http.get(SEARCH_API.format(encodeuri(name)), headers=headers) as resp:
      search_data = await resp.json()
    if "result" not in search_data.get("data", {}):
      await bilibili_check.finish(f"找不到用户：{name}")
    uid = search_data["data"]["result"][0]["mid"]

  async with http.get(FOLLOW_API.format(uid)) as resp:
    follow_data = await resp.json(content_type=None)
  async with http.get(MEDAL_API.format(uid), headers=headers) as resp:
    medal_data = await resp.json()
  async with http.get(follow_data["card"]["face"]) as resp:
    avatar_data = await resp.read()
  name: str = follow_data["card"]["name"]
  fans: int = follow_data["card"]["fans"]
  following: int = follow_data["card"]["attention"]
  following_list: List[int] = follow_data["card"]["attentions"]
  private = following != 0 and not following_list
  vtb_names = STATE().name_cache
  vtbs = sorted((
    (uid, vtb_names[uid]) for uid in following_list if uid in vtb_names
  ), key=lambda x: x[1])
  medals: Dict[int, Medal] = {}
  for i in medal_data["data"]["list"]:
    info = i["medal_info"]
    medals[info["target_id"]] = Medal(
      info["level"], info["medal_name"],
      info["medal_color_start"], info["medal_color_end"], info["medal_color_border"]
    )

  def make() -> MessageSegment:
    avatar = Image.open(BytesIO(avatar_data))
    items = [make_list_item(name, uid, medals.get(uid, None)) for uid, name in vtbs]
    header = make_header(avatar, name, uid, fans, following, len(vtbs))

    if not items:
      if private:
        items.append(textutil.render("关注列表不公开", "sans", 32))
      else:
        items.append(textutil.render("什么都查不到", "sans", 32))

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

    y = margin + header.height + gap
    im.paste((238, 238, 238), (margin, y, im.width - margin, y + list_height))

    x = margin + 2
    y += 2
    for i, item in enumerate(items):
      item_height = item.height + y_padding * 2
      if i % 2 == 0:
        im.paste((255, 255, 255), (x, y, im.width - margin - border, y + item_height))
      else:
        im.paste((247, 247, 247), (x, y, im.width - margin - border, y + item_height))
      im.paste(item, (x + x_padding, y + y_padding), item)
      y += item_height

    return imutil.to_segment(im)

  await bilibili_check.finish(await misc.to_thread(make))
