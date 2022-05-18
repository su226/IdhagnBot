from typing import Callable, Literal
from io import BytesIO
import platform
import time

from aiohttp import ClientSession
from PIL import Image, ImageDraw
from pydantic import Field
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
import nonebot
import psutil

from util.config import BaseConfig
from util import resources, helper, command
from .gpu import get_gpu_info

Items = Literal[
  "system",
  "uptime",
  "cpu",
  "cpu_usage",
  "gpus_and_usage",
  "memory",
  "swap",
  "python",
  "nonebot",
  "idhagnbot",
  "bot_uptime"
]

class Config(BaseConfig):
  __file__ = "idhagn_fetch"
  avatar_size: int = 320
  enable_header: bool = True
  enable_account: bool = True
  items: list[Items] = Field(default_factory=lambda: [
    "system",
    "uptime",
    "cpu",
    "cpu_usage",
    "gpus_and_usage",
    "memory",
    "swap",
    "python",
    "nonebot",
    "idhagnbot",
    "bot_uptime"
  ])
  background_color: int = 0x212121
  primary_color: int = 0x80d8ff
  secondary_color: int = 0xffffff

CONFIG = Config.load()

uname = platform.uname()
system_str = f"{uname.system} {uname.release}"
cpu_model_str = uname.processor or uname.machine
if uname.system == "Linux":
  system_str += f" ({platform.freedesktop_os_release()['NAME']})"
if uname.system in ("Linux", "Darwin"):
  with open("/proc/cpuinfo") as f:
    for i in f:
      if i.startswith("model name"):
        cpu_model_str = i.split(": ", 1)[1][:-1]
        break
python_str = f"{platform.python_version()} {platform.python_implementation()}[{platform.python_compiler()}]"
idhagnbot_str = "0.0.1-IDontKnow"
if nonebot.get_driver().env == "prod":
  idhagnbot_str += " (生产环境)"
else:
  idhagnbot_str += " (开发环境)"

def get_cpu_usage():
  cpu_util = round(psutil.cpu_percent())
  cpu_freq = round(psutil.cpu_freq().current * 1024)
  temps = psutil.sensors_temperatures()
  if "k10temp" in temps: # AMD
    cpu_temp = f"{round(temps['k10temp'][0].current)}°C"
  elif "coretemp" in temps: # Intel
    cpu_temp = f"{round(temps['coretemp'][0].current)}°C"
  else:
    cpu_temp = "温度未知"
  return [("CPU占用", f"{cpu_util}% {cpu_freq}MHz {cpu_temp}")]

def get_gpus_and_usage():
  segments = []
  try:
    infos = get_gpu_info()
    for i, info in enumerate(infos, 1):
      gpuid = "GPU" if len(infos) == 1 else f"GPU{i}"
      if info.unknown:
        segments.append((gpuid, info.model))
        segments.append((f"{gpuid}占用", "未知"))
      else:
        segments.append((gpuid, info.model))
        segments.append((f"{gpuid}占用", f"{info.percent}% {info.temp}°C {info.clk // 1000000}MHz (显存: {info.mem_percent}%)"))
  except:
    logger.opt(exception=True).warning("获取GPU信息失败")
  return segments

def get_memory():
  memory_info = psutil.virtual_memory()
  return [("内存", f"{round(memory_info.used / MEGA)}MiB / {round(memory_info.total / MEGA)}MiB ({round(memory_info.percent)}%)")]

def get_swap():
  swap_info = psutil.swap_memory()
  return [("交换", f"{round(swap_info.used / MEGA)}MiB / {round(swap_info.total / MEGA)}MiB ({round(swap_info.percent)}%)")]

ITEMS: dict[Items, Callable[[], list[tuple[str, str]]]] = {
  "system": lambda: [("系统", system_str)],
  "uptime": lambda: [("系统在线", helper.format_time(time.time() - psutil.boot_time()))],
  "cpu": lambda: [("CPU", cpu_model_str)],
  "cpu_usage": get_cpu_usage,
  "gpus_and_usage": get_gpus_and_usage,
  "memory": get_memory,
  "swap": get_swap,
  "python": lambda: [("Python", python_str)],
  "nonebot": lambda: [("Nonebot", nonebot.__version__)],
  "idhagnbot": lambda: [("IdhagnBot", idhagnbot_str)],
  "bot_uptime": lambda: [("机器人在线", helper.format_time(time.time() - bot_start_time))]
}

KILO = 1024
MEGA = 1024 ** 2
GIGA = 1024 ** 3
bot_start_time = time.time()

INFO = "IdhagnFetch - 绝对不是参考的screenfetch或者neofetch"

def color_to_pil(color: int) -> tuple[int, int, int]:
  return (color >> 16, (color >> 8) & 0xff, color & 0xff)

idhagnfetch = (command.CommandBuilder("idhagnfetch", "idhagnfetch", "状态", "state", "运行时间", "uptime")
  .brief("显示机器人的状态")
  .usage('''\
服务器在线在重启系统（含崩溃自动重启）时归零
机器人在线在重启机器人（含重启系统）时归零''')
  .build())
@idhagnfetch.handle()
async def handle_uptime(bot: Bot):
  items = []
  for name in CONFIG.items:
    items.extend(ITEMS[name]())
  font = resources.font("sans", 32)
  bold_font = resources.font("sans-bold", 32)
  max_width, line_height = font.getsize(INFO)
  for name, value in items:
    max_width = max(max_width, bold_font.getsize(name)[0] + font.getsize(f": {value}")[0])
  top_padding = 64
  left_padding = 64
  info_height = line_height * len(items) + font.getmetrics()[1]
  if CONFIG.enable_account:
    top_padding += line_height + 16
  if CONFIG.avatar_size:
    left_padding += CONFIG.avatar_size * 2 + 32
  if CONFIG.enable_header:
    info_height += line_height
  image_width = 64 + left_padding + max_width
  image_height = 64 + top_padding + max(info_height, CONFIG.avatar_size * 2)
  im = Image.new("RGB", (image_width, image_height), color_to_pil(CONFIG.background_color))
  draw = ImageDraw.Draw(im)
  draw.text((64, 64), INFO, color_to_pil(CONFIG.secondary_color), font)
  info = await bot.get_login_info()
  if CONFIG.avatar_size != 0:
    async with ClientSession() as http:
      response = await http.get(f"https://q1.qlogo.cn/g?b=qq&nk={info['user_id']}&s=0")
      avatar = Image.open(BytesIO(await response.read()))
    avatar_size = CONFIG.avatar_size * 2
    avatar = avatar.resize((avatar_size, avatar_size), Image.ANTIALIAS).convert("RGBA")
    im.paste(avatar, (64, top_padding), avatar)
  if CONFIG.enable_account:
    top_padding += line_height + 16
    name_width = bold_font.getsize(info["nickname"])[0]
    uid_str = f"({info['user_id']})"
    line_width = name_width + font.getsize(uid_str)[0]
    draw.text((left_padding, top_padding - line_height - 16), info["nickname"], color_to_pil(CONFIG.primary_color), bold_font)
    draw.text((left_padding + name_width, top_padding - line_height - 16), uid_str, color_to_pil(CONFIG.secondary_color), font)
    draw.rectangle((left_padding, top_padding - 6, left_padding + line_width, top_padding - 5), color_to_pil(CONFIG.secondary_color))
  for i, (name, value) in enumerate(items):
    name_width = bold_font.getsize(name)[0]
    draw.text((left_padding, top_padding + i * line_height), name, color_to_pil(CONFIG.primary_color), bold_font)
    draw.text((left_padding + name_width, top_padding + i * line_height), f": {value}", color_to_pil(CONFIG.secondary_color), font)
  f = BytesIO()
  im.save(f, "PNG")
  await idhagnfetch.finish(MessageSegment.image(f))
