import asyncio
import itertools
import platform
import re
import time
from typing import (
  Any, Awaitable, Callable, Generator, Iterable, List, Literal, Mapping, Sequence, Set, Tuple,
  TypeVar,
)

import nonebot
import psutil
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from PIL import Image
from psutil._common import sdiskpart  # type: ignore
from pydantic import BaseModel, Field

from util import colorutil, command, configs, imutil, misc, textutil

from .gpu import get_gpu_info

Item = Tuple[str, str]
BarItem = Tuple[str, str, float]
Items = Literal[
  "system",
  "uptime",
  "cpu",
  "cpu_usage",
  "gpus",
  "gpus_and_usage",
  "memory",
  "swap",
  "disks",
  "disks_aggregate",
  "battery",
  "diskio",
  "network",
  "backend",
  "backend_stats",
  "python",
  "nonebot",
  "idhagnbot",
  "bot_uptime",
]
BarItems = Literal[
  "cpu",
  "memory",
  "swap",
  "disks",
  "disks_aggregate",
  "battery",
]


class Config(BaseModel):
  avatar_size: int = 640
  header: str = "IdhagnFetch - 绝对不是参考的screenfetch或者neofetch"
  enable_account: bool = True
  items: List[Items] = Field(default_factory=lambda: [
    "system",
    "uptime",
    "cpu",
    "gpus_and_usage",
    "disks",
    "diskio",
    "network",
    "backend",
    "backend_stats",
    "python",
    "nonebot",
    "bot_uptime",
  ])
  bar_items: List[BarItems] = Field(default_factory=lambda: [
    "cpu",
    "memory",
    "swap",
  ])
  columns: int = 3
  ignore_loop_device: bool = True
  ignore_bind_mount: bool = True
  ignored_disks: Set[str] = Field(default_factory=set)
  background_color: int = 0x212121
  primary_color: int = 0x80d8ff
  secondary_color: int = 0xffffff
  bar_color: int = 0x424242

  def format(self, primary: str, secondary: str) -> str:
    return (
      f"<span color='#{self.primary_color:06x}' weight='bold'>{textutil.escape(primary)}</span>"
      f"<span color='#{self.secondary_color:06x}'>{textutil.escape(secondary)}</span>"
    )


def _get_distro() -> str:
  def _parse_os_release(lines: Iterable[str]):
    info = {}
    for line in lines:
      if match := _os_release_line.match(line):
        info[match["name"]] = _os_release_unescape.sub(r"\1", match["value"])
    return info

  _os_release_line = re.compile(
    r"^(?P<name>[a-zA-Z0-9_]+)=(?P<quote>[\"\']?)(?P<value>.*)(?P=quote)$",
  )
  _os_release_unescape = re.compile(r"\\([\\\$\"\'`])")
  _os_release_candidates = ("/etc/os-release", "/usr/lib/os-release")
  errno = None
  for candidate in _os_release_candidates:
    try:
      with open(candidate, encoding="utf-8") as f:
        _os_release = _parse_os_release(f)
      break
    except OSError as e:
      errno = e.errno
  else:
    raise OSError(errno, f"Unable to read files {', '.join(_os_release_candidates)}")

  if "PRETTY_NAME" in _os_release:
    return _os_release["PRETTY_NAME"]
  return _os_release["NAME"]


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


def human_util(used: int, total: int) -> str:
  if total < 1024:
    return f"{used}/{total}B"
  units = ("K", "M", "G", "T", "P", "E", "Z", "Y")
  unit = units[0]
  used_f = used
  total_f = total
  for unit in units:
    used_f /= 1024
    total_f /= 1024
    if total_f < 1024:
      break
  return f"{used_f:.1f}/{total_f:.1f}{unit}iB"


CONFIG = configs.SharedConfig("idhagnfetch", Config)
_uname = platform.uname()
SYSTEM = f"{_uname.system} {_uname.release}"
CPU_MODEL = _uname.processor or _uname.machine
if _uname.system == "Linux":
  try:
    SYSTEM += f" ({_get_distro()})"
  except (OSError, KeyError):
    pass
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
T = TypeVar("T")


def simple(fn: Callable[[], T]) -> Callable[[Bot], Awaitable[List[T]]]:
  async def get_simple(bot: Bot) -> List[T]:
    return [fn()]
  return get_simple


async def get_cpu_bar(bot: Bot) -> Sequence[BarItem]:
  psutil.cpu_percent()
  await asyncio.sleep(1)
  cpu_util = psutil.cpu_percent()
  cpu_freq = psutil.cpu_freq().current
  cpu_freq = f"{round(cpu_freq / 1000, 1)}GHz" if cpu_freq > 1000 else f"{round(cpu_freq)}MHz"
  temps = psutil.sensors_temperatures()
  cpu_temp = ""
  if "k10temp" in temps:  # AMD
    cpu_temp = f" {round(temps['k10temp'][0].current)}°C"
  elif "coretemp" in temps:  # Intel
    cpu_temp = f" {round(temps['coretemp'][0].current)}°C"
  return [("CPU", f"{round(cpu_util)}% {cpu_freq}{cpu_temp}", cpu_util / 100)]


async def get_cpu_usage(bot: Bot) -> List[Item]:
  return [("CPU占用", (await get_cpu_bar(bot))[0][1])]


async def get_gpus(bot: Bot) -> List[Item]:
  segments = []
  infos = get_gpu_info()
  for i, info in enumerate(infos, 1):
    gpuid = "GPU" if len(infos) == 1 else f"GPU{i}"
    segments.append((gpuid, info.model))
  return segments


async def get_gpus_and_usage(bot: Bot) -> List[Item]:
  segments = []
  infos = get_gpu_info()
  for i, info in enumerate(infos, 1):
    gpuid = "GPU" if len(infos) == 1 else f"GPU{i}"
    segments.append((gpuid, info.model))
    if not info.unknown:
      freq = info.clk / 1000000
      freq = f"{int(freq)}MHz" if freq < 1000 else f"{freq / 1000:.1f}GHz"
      segments.append(
        (f"{gpuid}占用", f"{info.percent}% {freq} {info.temp}°C (显存: {info.mem_percent}%)"),
      )
  return segments


async def get_memory_bar(bot: Bot) -> List[BarItem]:
  mem_info = psutil.virtual_memory()
  info_str = (
    f"{human_util(mem_info.used, mem_info.total)} {round(mem_info.percent)}%"
  )
  return [("内存", info_str, mem_info.percent / 100)]


async def get_memory(bot: Bot) -> List[Item]:
  mem_info = psutil.virtual_memory()
  info_str = (
    f"{human_util(mem_info.used, mem_info.total)} ({round(mem_info.percent)}%)"
  )
  return [("内存", info_str)]


async def get_swap_bar(bot: Bot) -> List[BarItem]:
  swap_info = psutil.swap_memory()
  info_str = (
    f"{human_util(swap_info.used, swap_info.total)} {round(swap_info.percent)}%"
  )
  return [("交换", info_str, swap_info.percent / 100)]


async def get_swap(bot: Bot) -> List[Item]:
  swap_info = psutil.swap_memory()
  info_str = (
    f"{human_util(swap_info.used, swap_info.total)} ({round(swap_info.percent)}%)"
  )
  return [("交换", info_str)]


def iter_disks() -> Generator[sdiskpart, Any, Any]:
  config = CONFIG()
  shown: Set[str] = set()
  for partition in psutil.disk_partitions():
    if config.ignore_loop_device and partition.device.startswith("/dev/loop"):
      continue
    if config.ignore_bind_mount and partition.device in shown:
      continue
    shown.add(partition.device)
    if partition.device in config.ignored_disks:
      continue
    yield partition


async def get_disks(bot: Bot) -> List[Item]:
  lines: List[Item] = []
  for partition in iter_disks():
    usage = psutil.disk_usage(partition.mountpoint)
    info_str = f"{human_util(usage.used, usage.total)} ({round(usage.percent)}%)"
    lines.append((partition.mountpoint, info_str))
  return lines


async def get_disks_bar(bot: Bot) -> List[BarItem]:
  lines: List[BarItem] = []
  for partition in iter_disks():
    usage = psutil.disk_usage(partition.mountpoint)
    info_str = f"{human_util(usage.used, usage.total)} {round(usage.percent)}%"
    lines.append((partition.mountpoint, info_str, usage.percent / 100))
  return lines


async def get_disks_aggregate(bot: Bot) -> List[Item]:
  used = 0
  total = 0
  for partition in iter_disks():
    usage = psutil.disk_usage(partition.mountpoint)
    used += usage.used
    total += usage.total
  return [(("存储", f"{human_util(used, total)} ({round(used / total * 100)}%)"))]


async def get_disks_aggregate_bar(bot: Bot) -> List[BarItem]:
  used = 0
  total = 0
  for partition in iter_disks():
    usage = psutil.disk_usage(partition.mountpoint)
    used += usage.used
    total += usage.total
  ratio = used / total
  return [("存储", f"{human_util(used, total)} {round(ratio * 100)}%", ratio)]


async def get_battery(bot: Bot) -> List[Item]:
  battery_info = psutil.sensors_battery()
  if not battery_info:
    return []
  percent = round(battery_info.percent, 1)
  if battery_info.power_plugged:
    info_str = f"{percent}% (充电中)"
  else:
    info_str = f"{percent}% (剩余 {misc.format_time(battery_info.secsleft)})"
  return [("电池", info_str)]


async def get_battery_bar(bot: Bot) -> List[BarItem]:
  battery_info = psutil.sensors_battery()
  if not battery_info:
    return []
  percent = round(battery_info.percent, 1)
  if battery_info.power_plugged:
    info_str = f"充电中 {percent}%"
  else:
    info_str = f"{misc.format_time(battery_info.secsleft)} {percent}%"
  return [("电池", info_str, battery_info.percent / 100)]


async def get_diskio(bot: Bot) -> List[Item]:
  counter = psutil.disk_io_counters()
  if not counter:
    return []
  await asyncio.sleep(1)
  counter1 = psutil.disk_io_counters()
  if not counter1:
    return []
  read = counter1.read_bytes - counter.read_bytes
  write = counter1.write_bytes - counter.write_bytes
  return [("硬盘", f"读 {human_size(read)}/s 写 {human_size(write)}/s")]


async def get_network(bot: Bot) -> List[Item]:
  before = psutil.net_io_counters(True)
  await asyncio.sleep(1)
  after = psutil.net_io_counters(True)
  after.pop("lo", None)
  counters = [(counter, before[name]) for name, counter in after.items()]
  recv = sum(x.bytes_recv - y.bytes_recv for x, y in counters)
  sent = sum(x.bytes_sent - y.bytes_sent for x, y in counters)
  return [("网络", f"↓ {human_size(recv)}/s ↑ {human_size(sent)}/s")]


async def get_backend(bot: Bot) -> List[Item]:
  version = await bot.get_version_info()
  return [("后端", f"{version['app_name']} {version['app_version']}")]


async def get_backend_stats(bot: Bot) -> List[Item]:
  status = await bot.get_status()
  if "stat" not in status:
    return []
  stats = status["stat"]
  lost_ratio = stats["packet_lost"] / (stats["packet_received"] + stats["packet_sent"])
  return [("后端状态", " ".join([
    f"收 {stats['message_received']}",
    f"发 {stats['message_sent']}",
    f"丢包 {round(lost_ratio * 100)}%",
    f"断连 {stats['disconnect_times']}",
    f"下线 {stats['lost_times']}",
  ]))]


ITEMS: Mapping[Items, Callable[[Bot], Awaitable[Sequence[Item]]]] = {
  "system": simple(lambda: ("系统", SYSTEM)),
  "uptime": simple(lambda: ("系统在线", misc.format_time(time.time() - psutil.boot_time()))),
  "cpu": simple(lambda: ("CPU", CPU_MODEL)),
  "cpu_usage": get_cpu_usage,
  "gpus": get_gpus,
  "gpus_and_usage": get_gpus_and_usage,
  "memory": get_memory,
  "swap": get_swap,
  "disks": get_disks,
  "disks_aggregate": get_disks_aggregate,
  "battery": get_battery,
  "diskio": get_diskio,
  "network": get_network,
  "backend": get_backend,
  "backend_stats": get_backend_stats,
  "python": simple(lambda: ("Python", PYTHON_VER)),
  "nonebot": simple(lambda: ("Nonebot", nonebot.__version__)),
  "idhagnbot": simple(lambda: ("IdhagnBot", IDHAGNBOT_VER)),
  "bot_uptime": simple(lambda: ("机器人在线", misc.format_time(time.time() - BOT_START_TIME))),
}
BAR_ITEMS: Mapping[BarItems, Callable[[Bot], Awaitable[Sequence[BarItem]]]] = {
  "cpu": get_cpu_bar,
  "memory": get_memory_bar,
  "swap": get_swap_bar,
  "disks": get_disks_bar,
  "disks_aggregate": get_disks_aggregate_bar,
  "battery": get_battery_bar,
}


def render_bars(min_width: int, items: Iterable[BarItem]) -> Image.Image:
  BAR_GAP = 32
  BAR_PADDING = 4
  BAR_HEIGHT = 4
  config = CONFIG()
  lines: List[Tuple[List[Tuple[Image.Image, Image.Image, float]], int]] = []
  height = 0
  for line in misc.chunked(items, config.columns):
    rendered_line: List[Tuple[Image.Image, Image.Image, float]] = []
    item_w = 0
    line_h = 0
    for name, value, ratio in line:
      name_im = textutil.render(name + " ", "sans bold", 32, color=config.primary_color)
      value_im = textutil.render(value, "sans", 32, color=config.secondary_color)
      item_w = max(item_w, name_im.width + value_im.width)
      line_h = max(line_h, name_im.height, value_im.height)
      rendered_line.append((name_im, value_im, ratio))
    lines.append((rendered_line, line_h))
    height += line_h + BAR_PADDING + BAR_HEIGHT
    min_width = max(min_width, item_w * len(line) + max(len(line) - 1, 0) * BAR_GAP)
  im = Image.new("RGBA", (min_width, height))
  fg_color = colorutil.split_rgb(config.primary_color)
  bg_color = colorutil.split_rgb(config.bar_color)
  y = 0
  for line, line_h in lines:
    item_w = (im.width - max(len(line) - 1, 0) * BAR_GAP) // len(line)
    text_y = y + line_h / 2
    bar_y1 = y + line_h + BAR_PADDING
    bar_y2 = bar_y1 + BAR_HEIGHT
    for i, (name, value, ratio) in enumerate(line):
      x = i * (im.width - item_w) // (len(line) - 1) if len(line) > 1 else 0
      im.paste(name, (x, int(text_y - name.height / 2)))
      im.paste(value, (x + item_w - value.width, int(text_y - value.height / 2)))
      bar_w = round(ratio * item_w)
      im.paste(fg_color, (x, bar_y1, x + bar_w, bar_y2))
      im.paste(bg_color, (x + bar_w, bar_y1, x + item_w, bar_y2))
    y = bar_y2
  return im


idhagnfetch = (
  command.CommandBuilder(
    "idhagnfetch", "idhagnfetch", "状态", "status", "state", "运行时间", "uptime",
  )
  .brief("显示机器人的状态")
  .usage('''\
服务器在线在重启系统（含崩溃自动重启）时归零
机器人在线在重启机器人（含重启系统）时归零''')
  .build()
)
@idhagnfetch.handle()
async def handle_idhagnfetch(bot: Bot):
  config = CONFIG()
  login, avatar = await asyncio.gather(
    bot.get_login_info(),
    imutil.get_avatar(int(bot.self_id)),
  )
  # 分开获取，防止干扰网络信息
  items, bar_items = await asyncio.gather(
    asyncio.gather(*(ITEMS[name](bot) for name in config.items)),
    asyncio.gather(*(BAR_ITEMS[name](bot) for name in config.bar_items)),
  )

  def make() -> MessageSegment:
    nonlocal avatar
    info_lines = []
    for item in items:
      info_lines.extend(config.format(title + ": ", value) for title, value in item)

    info_im = textutil.render("\n".join(info_lines), "sans", 32, markup=True)
    info_w, info_h = info_im.size
    im_w = 128
    im_h = 128
    header_im = misc.any_v
    account_im = misc.any_v
    bar_im = misc.any_v
    if config.header:
      header_im = textutil.render(config.header, "sans", 32, color=(255, 255, 255))
      im_w = max(im_w, header_im.width + 128)
      im_h += header_im.height + 16
    if config.enable_account:
      account_markup = config.format(login["nickname"], f"({login['user_id']})")
      account_im = textutil.render(account_markup, "sans", 32, markup=True)
      info_w = max(info_w, account_im.width)
      info_h += account_im.height + 16
    if config.avatar_size:
      info_w += config.avatar_size + 32
      info_h = max(info_h, config.avatar_size)
    im_w = max(im_w, info_w + 128)
    im_h += info_h
    if bar_items:
      bar_im = render_bars(im_w - 128, itertools.chain.from_iterable(bar_items))
      im_w = max(im_w, bar_im.width + 128)
      im_h += bar_im.height + 32

    im = Image.new("RGB", (im_w, im_h), colorutil.split_rgb(config.background_color))
    x = 64
    y = 64
    if config.header:
      im.paste(header_im, (x, y), header_im)
      y += header_im.height + 16
    if bar_items:
      im.paste(bar_im, (x, y), bar_im)
      y += bar_im.height + 32
    if config.avatar_size != 0:
      avatar = avatar.resize((config.avatar_size, config.avatar_size), imutil.scale_resample())
      im.paste(avatar, (x, y), avatar)
      x += config.avatar_size + 32
    if config.enable_account:
      im.paste(account_im, (x, y), account_im)
      im.paste(colorutil.split_rgb(config.secondary_color), (
        x, y + account_im.height + 6,
        x + account_im.width, y + account_im.height + 10,
      ))
      y += account_im.height + 16
    im.paste(info_im, (x, y), info_im)
    return imutil.to_segment(im)

  await idhagnfetch.finish(await misc.to_thread(make))
