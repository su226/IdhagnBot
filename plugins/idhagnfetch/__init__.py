import asyncio
import html
import platform
import time
from typing import Any, Callable, Literal, get_args

import nonebot
import psutil
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from PIL import Image
from pydantic import BaseModel, Field

from util import colorutil, command, configs, imutil, misc, textutil

from .gpu import get_gpu_info

Items = Literal[
  "system",
  "uptime",
  "cpu",
  "cpu_usage",
  "gpus_and_usage",
  "memory",
  "swap",
  "disks",
  "battery",
  "python",
  "nonebot",
  "idhagnbot",
  "bot_uptime"
]


class Config(BaseModel):
  avatar_size: int = 320
  enable_header: bool = True
  enable_account: bool = True
  items: list[Items] = Field(default_factory=lambda: list(get_args(Items)))
  background_color: int = 0x212121
  primary_color: int = 0x80d8ff
  secondary_color: int = 0xffffff

  def format(self, primary: str, secondary: str) -> str:
    return (
      f"<span color='#{self.primary_color:06x}' weight='bold'>{html.escape(primary)}</span>"
      f"<span color='#{self.secondary_color:06x}'>{html.escape(secondary)}</span>"
    )


CONFIG = configs.SharedConfig("idhagnfetch", Config)
HEADER = "IdhagnFetch - 绝对不是参考的screenfetch或者neofetch"
KILO = 1024
MEGA = 1024 ** 2
GIGA = 1024 ** 3

_uname = platform.uname()
SYSTEM = f"{_uname.system} {_uname.release}"
CPU_MODEL = _uname.processor or _uname.machine
if _uname.system == "Linux":
  SYSTEM += f" ({platform.freedesktop_os_release()['NAME']})"
if _uname.system in ("Linux", "Darwin"):
  with open("/proc/cpuinfo") as f:
    for i in f:
      if i.startswith("model name"):
        CPU_MODEL = i.split(": ", 1)[1][:-1]
        break
del _uname
PYTHON_VER = (
  f"{platform.python_version()} {platform.python_implementation()}[{platform.python_compiler()}]"
)
IDHAGNBOT_VER = "0.0.1-IDontKnow"
if nonebot.get_driver().env == "prod":
  IDHAGNBOT_VER += " (生产环境)"
else:
  IDHAGNBOT_VER += " (开发环境)"
BOT_START_TIME = time.time()


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
    else:
      segments.append((gpuid, info.model))
      segments.append((
        f"{gpuid}占用",
        f"{info.percent}% {info.temp}°C {info.clk // 1000000}MHz (显存: {info.mem_percent}%)"
      ))
  return segments


def get_memory():
  mem_info = psutil.virtual_memory()
  info_str = (
    f"{round(mem_info.used / MEGA)}MiB / {round(mem_info.total / MEGA)}MiB"
    f" ({round(mem_info.percent)}%)"
  )
  return [("内存", info_str)]


def get_swap():
  swap_info = psutil.swap_memory()
  info_str = (
    f"{round(swap_info.used / MEGA)}MiB / {round(swap_info.total / MEGA)}MiB"
    f" ({round(swap_info.percent)}%)"
  )
  return [("交换", info_str)]


def human_size(byte: int) -> str:
  if byte < 1024:
    return f"{byte}B"
  units = ("K", "M", "G", "T", "P", "E", "Z", "Y")
  unit = units[0]
  value = byte
  for unit in units:
    value /= 1024
    if value < 1024:
      break
  return f"{value:.1f}{unit}iB"


def get_disks():
  lines: list[tuple[str, str]] = []
  for partition in psutil.disk_partitions():
    usage = psutil.disk_usage(partition.mountpoint)
    info_str = f"{human_size(usage.used)} / {human_size(usage.total)} ({usage.percent}%)"
    lines.append((partition.mountpoint, info_str))
  return lines


def get_battery():
  battery_info = psutil.sensors_battery()
  if not battery_info:
    return []
  percent = round(battery_info.percent, 1)
  if battery_info.power_plugged:
    info_str = f"{percent}% (充电中)"
  else:
    info_str = f"{percent}% (剩余 {misc.format_time(battery_info.secsleft)})"
  return [("电池", info_str)]


ITEMS: dict[Items, Callable[[], list[tuple[str, str]]]] = {
  "system": lambda: [("系统", SYSTEM)],
  "uptime": lambda: [("系统在线", misc.format_time(time.time() - psutil.boot_time()))],
  "cpu": lambda: [("CPU", CPU_MODEL)],
  "cpu_usage": get_cpu_usage,
  "gpus_and_usage": get_gpus_and_usage,
  "memory": get_memory,
  "swap": get_swap,
  "disks": get_disks,
  "battery": get_battery,
  "python": lambda: [("Python", PYTHON_VER)],
  "nonebot": lambda: [("Nonebot", nonebot.__version__)],
  "idhagnbot": lambda: [("IdhagnBot", IDHAGNBOT_VER)],
  "bot_uptime": lambda: [("机器人在线", misc.format_time(time.time() - BOT_START_TIME))]
}


idhagnfetch = (
  command.CommandBuilder("idhagnfetch", "idhagnfetch", "状态", "state", "运行时间", "uptime")
  .brief("显示机器人的状态")
  .usage('''\
服务器在线在重启系统（含崩溃自动重启）时归零
机器人在线在重启机器人（含重启系统）时归零''')
  .build()
)
@idhagnfetch.handle()
async def handle_idhagnfetch(bot: Bot):
  login, avatar = await asyncio.gather(bot.get_login_info(), imutil.get_avatar(int(bot.self_id)))

  def make() -> MessageSegment:
    nonlocal avatar
    config = CONFIG()
    info_lines = []
    for name in config.items:
      info_lines.extend(config.format(title + ": ", value) for title, value in ITEMS[name]())

    info_x = 64
    info_y = 64
    info_im = textutil.render("\n".join(info_lines), "sans", 32, markup=True)
    info_w, info_h = info_im.size
    im_w = 128
    _bound: Any = None  # HACK
    header_im = _bound
    account_im = _bound
    if config.enable_header:
      header_im = textutil.render(HEADER, "sans", 32, color=(255, 255, 255))
      im_w += header_im.width
      info_y += header_im.height + 16
    if config.enable_account:
      account_markup = config.format(login["nickname"], f"({login['user_id']})")
      account_im = textutil.render(account_markup, "sans", 32, markup=True)
      info_w = max(info_w, account_im.width)
      info_h += account_im.height + 16
    if config.avatar_size:
      info_x += config.avatar_size * 2 + 32
      info_h = max(info_h, config.avatar_size * 2)
    im_w = max(im_w, info_x + info_w + 64)
    im_h = info_y + info_h + 64

    im = Image.new("RGB", (im_w, im_h), colorutil.split_rgb(config.background_color))
    if config.enable_header:
      im.paste(header_im, (64, 64), header_im)
    if config.avatar_size != 0:
      avatar_size = config.avatar_size * 2
      avatar = avatar.resize((avatar_size, avatar_size), imutil.scale_resample())
      im.paste(avatar, (64, info_y), avatar)
    if config.enable_account:
      im.paste(account_im, (info_x, info_y), account_im)
      im.paste(colorutil.split_rgb(config.secondary_color), (
        info_x, info_y + account_im.height + 6,
        info_x + account_im.width, info_y + account_im.height + 10
      ))
      info_y += account_im.height + 16
    im.paste(info_im, (info_x, info_y), info_im)

    return imutil.to_segment(im)

  await idhagnfetch.finish(await asyncio.to_thread(make))
