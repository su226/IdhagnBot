import random
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg
from PIL import Image
from pydantic import BaseModel, Field

from util import colorutil, command, configs, imutil, misc, textutil


class Config(BaseModel):
  brand_enable: bool = True
  brand_cache_duration: timedelta = timedelta(1)
  simpleicons_data_url: str = (
    "https://github.com/simple-icons/simple-icons/raw/develop/_data/simple-icons.json"
  )


class State(BaseModel):
  last_update: datetime = datetime.min
  brand_to_color: Dict[str, int] = Field(default_factory=dict)
  color_to_brands: Dict[int, List[str]] = Field(default_factory=dict)


CONFIG = configs.SharedConfig("color", Config)
STATE = configs.SharedState("color", State)
TITLE_TO_SLUG_REPLACEMENTS = {
  '+': 'plus',
  '.': 'dot',
  '&': 'and',
  'đ': 'd',
  'ħ': 'h',
  'ı': 'i',
  'ĸ': 'k',
  'ŀ': 'l',
  'ł': 'l',
  'ß': 'ss',
  'ŧ': 't',
}
TITLE_TO_SLUG_CHARS_REGEX = re.compile(f"[{''.join(TITLE_TO_SLUG_REPLACEMENTS)}]")
TITLE_TO_SLUG_RANGE_REGEX = re.compile(r"[^a-z0-9_]")


def title_to_slug(title: str) -> str:
  def sub(match: re.Match[str]) -> str:
    return TITLE_TO_SLUG_REPLACEMENTS[match[0]]
  slug = TITLE_TO_SLUG_CHARS_REGEX.sub(sub, title.lower())
  slug = unicodedata.normalize("NFD", slug)
  slug = TITLE_TO_SLUG_RANGE_REGEX.sub("", slug)
  return slug


async def update_brand() -> None:
  config = CONFIG()
  state = STATE()
  state.brand_to_color.clear()
  state.color_to_brands.clear()
  state.last_update = datetime.now()
  http = misc.http()
  async with http.get(config.simpleicons_data_url) as response:
    data = await response.json(content_type=None)
    icons = data["icons"]
  for icon in icons:
    title = icon["title"]
    slug = icon["slug"] if "slug" in icon else title_to_slug(icon["title"])
    color = int(icon["hex"], 16)
    state.brand_to_color[slug] = color
    if color not in state.color_to_brands:
      state.color_to_brands[color] = [title]
    else:
      state.color_to_brands[color].append(title)
  for icon in icons:
    title = title_to_slug(icon["title"])
    if title not in state.brand_to_color:
      state.brand_to_color[title] = int(icon["hex"], 16)
  STATE.dump()


def color_img_usage() -> str:
  usage = '''\
支持多种格式，比如以下均为蓝色
/色图 #0000ff
/色图 0000ff
/色图 #00f
/色图 00f
/色图 rgb(0, 0, 255)
/色图 hsl(240, 100%, 50%)
/色图 blue'''
  if CONFIG().brand_enable:
    usage += "\n也可以使用 simpleicons.org 上的品牌色"
  return usage
color_img = (
  command.CommandBuilder("color", "色图", "color")
  .brief("哎哟这个色啊！好色！")
  .usage(color_img_usage)
  .build()
)
@color_img.handle()
async def handle_color_img(arg: Message = CommandArg()):
  config = CONFIG()
  color_str = arg.extract_plain_text().rstrip()
  if color_str:
    value = colorutil.parse(color_str)
    if value is None and config.brand_enable:
      state = STATE()
      if datetime.now() - state.last_update > config.brand_cache_duration:
        await update_brand()
      if (slug := title_to_slug(color_str)) in state.brand_to_color:
        value = state.brand_to_color[slug]
    if value is None:
      await color_img.finish(f"未知颜色：{color_str}")
  else:
    value = random.randint(0, 0xffffff)
  r, g, b = colorutil.split_rgb(value)
  h, s, l = colorutil.rgb2hsl(r, g, b)

  def make() -> MessageSegment:
    im = Image.new("RGB", (1000, 1000), (r, g, b))
    markup = f'''\
<span size="200%">#{value:06x}</span>
rgb({r}, {g}, {b})
hsl({h:.1f}deg, {s * 100:.1f}%, {l * 100:.1f}%)'''
    if value in colorutil.NAMES:
      markup += f"\n{colorutil.NAMES[value]}"
    if config.brand_enable:
      state = STATE()
      if value in state.color_to_brands:
        if len(state.color_to_brands[value]) > 1:
          markup += f"\n品牌色: {len(state.color_to_brands[value])} 个品牌"
        else:
          markup += f"\n品牌色: {state.color_to_brands[value][0]}"
    fg = (255, 255, 255) if colorutil.luminance(r, g, b) < 0.5 else (0, 0, 0)
    textutil.paste(
      im, (im.width // 2, im.height // 2), markup, "sans", 64,
      markup=True, align="m", anchor="mm", color=fg
    )
    return imutil.to_segment(im)

  await color_img.finish(await misc.to_thread(make))
