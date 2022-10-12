import html
import platform
import time
from io import BytesIO
from typing import Any, Callable, Literal

import nonebot
import psutil
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from util import color, command, config_v2, text, util

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


class Config(BaseModel):
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

  def format(self, primary: str, secondary: str) -> str:
    return (
      f"<span color='#{self.primary_color:06x}' weight='bold'>{html.escape(primary)}</span>"
      f"<span color='#{self.secondary_color:06x}'>{html.escape(secondary)}</span>")


CONFIG = config_v2.SharedConfig("idhagn_fetch", Config)
HEADER = "IdhagnFetch - 绝对不是参考的screenfetch或者neofetch"
KILO = 1024
MEGA = 1024 ** 2
GIGA = 1024 ** 3

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
python_str = (
  f"{platform.python_version()} {platform.python_implementation()}[{platform.python_compiler()}]")
idhagnbot_str = "0.0.1-IDontKnow"
if nonebot.get_driver().env == "prod":
  idhagnbot_str += " (生产环境)"
else:
  idhagnbot_str += " (开发环境)"
bot_start_time = time.time()


def get_cpu_usage():
  cpu_util = round(psutil.cpu_percent())
  cpu_freq = round(psutil.cpu_freq().current)
  temps = psutil.sensors_temperatures()
  if "k10temp" in temps:  # AMD
    cpu_temp = f"{round(temps['k10temp'][0].current)}°C"
  elif "coretemp" in temps:  # Intel
    cpu_temp = f"{round(temps['coretemp'][0].current)}°C"
  else:
    cpu_temp = "温度未知"
  return [("CPU占用", f"{cpu_util}% {cpu_freq}MHz {cpu_temp}")]


def get_gpus_and_usage():
  segments = []
  infos = get_gpu_info()
  for i, info in enumerate(infos, 1):
    gpuid = "GPU" if len(infos) == 1 else f"GPU{i}"
    if info.unknown:
      segments.append((gpuid, info.model))
      segments.append((f"{gpuid}占用", "未知"))
    else:
      segments.append((gpuid, info.model))
      segments.append((
        f"{gpuid}占用",
        f"{info.percent}% {info.temp}°C {info.clk // 1000000}MHz (显存: {info.mem_percent}%)"))
  return segments


def get_memory():
  memory_info = psutil.virtual_memory()
  return [(
    "内存", f"{round(memory_info.used / MEGA)}MiB / {round(memory_info.total / MEGA)}MiB"
    f" ({round(memory_info.percent)}%)")]


def get_swap():
  swap_info = psutil.swap_memory()
  return [(
    "交换", f"{round(swap_info.used / MEGA)}MiB / {round(swap_info.total / MEGA)}MiB"
    f" ({round(swap_info.percent)}%)")]


ITEMS: dict[Items, Callable[[], list[tuple[str, str]]]] = {
  "system": lambda: [("系统", system_str)],
  "uptime": lambda: [("系统在线", util.format_time(time.time() - psutil.boot_time()))],
  "cpu": lambda: [("CPU", cpu_model_str)],
  "cpu_usage": get_cpu_usage,
  "gpus_and_usage": get_gpus_and_usage,
  "memory": get_memory,
  "swap": get_swap,
  "python": lambda: [("Python", python_str)],
  "nonebot": lambda: [("Nonebot", nonebot.__version__)],
  "idhagnbot": lambda: [("IdhagnBot", idhagnbot_str)],
  "bot_uptime": lambda: [("机器人在线", util.format_time(time.time() - bot_start_time))]
}
idhagnfetch = (
  command.CommandBuilder("idhagnfetch", "idhagnfetch", "状态", "state", "运行时间", "uptime")
  .brief("显示机器人的状态")
  .usage('''\
服务器在线在重启系统（含崩溃自动重启）时归零
机器人在线在重启机器人（含重启系统）时归零''')
  .build())


@idhagnfetch.handle()
async def handle_uptime(bot: Bot):
  config = CONFIG()
  info_lines = []
  for name in config.items:
    info_lines.extend(config.format(title + ": ", value) for title, value in ITEMS[name]())

  info_x = 64
  info_y = 64
  info_im = text.render("\n".join(info_lines), "sans", 32, markup=True)
  info_w, info_h = info_im.size
  login = await bot.get_login_info()
  _bound: Any = None  # HACK
  header_im = _bound
  account_im = _bound
  if config.enable_header:
    header_im = text.render(HEADER, "sans", 32, color=(255, 255, 255))
    info_w = max(info_w, header_im.width)
    info_y += header_im.height + 16
  if config.enable_account:
    account_markup = config.format(login["nickname"], f"({login['user_id']})")
    account_im = text.render(account_markup, "sans", 32, markup=True)
    info_w = max(info_w, account_im.width)
    info_h += account_im.height + 16
  if config.avatar_size:
    info_x += config.avatar_size * 2 + 32
    info_h = max(info_h, config.avatar_size * 2)
  im_w = info_x + info_w + 64
  im_h = info_y + info_h + 64

  im = Image.new("RGB", (im_w, im_h), color.split_rgb(config.background_color))
  if config.enable_header:
    im.paste(header_im, (64, 64), header_im)
  if config.avatar_size != 0:
    avatar = await util.get_avatar(login["user_id"])
    avatar_size = config.avatar_size * 2
    avatar = avatar.resize((avatar_size, avatar_size), util.scale_resample)
    im.paste(avatar, (64, info_y), avatar)
  if config.enable_account:
    im.paste(account_im, (info_x, info_y), account_im)
    ImageDraw.Draw(im).rectangle((
      info_x, info_y + account_im.height + 6,
      info_x + account_im.width, info_y + account_im.height + 9
    ), color.split_rgb(config.secondary_color))
    info_y += account_im.height + 16
  im.paste(info_im, (info_x, info_y), info_im)

  f = BytesIO()
  im.save(f, "PNG")
  await idhagnfetch.finish(MessageSegment.image(f))
