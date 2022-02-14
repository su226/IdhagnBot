from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
from nonebot.adapters.onebot.v11 import MessageSegment
import asyncio
import os
import nonebot
import psutil
import time
import subprocess
import platform

plugin_dir = os.path.dirname(os.path.abspath(__file__))
gpuload = os.path.join(plugin_dir, "gpuload")
kernel_str = os.uname().release
python_str = f"{platform.python_version()} {platform.python_implementation()}[{platform.python_compiler()}]"
idhagnbot_str = "0.0.1-IDontKnow"
font = ImageFont.truetype(os.path.join(plugin_dir, "Iosevka Term Extended.ttf"), 15)
color = (250, 250, 250)

KILO = 1024
MEGA = 1024 ** 2
GIGA = 1024 ** 3
bot_start_time = time.time()

uptime = nonebot.on_command("状态", aliases={"state", "运行时间", "uptime"})
uptime.__cmd__ = ["状态", "state", "运行时间", "uptime"]
uptime.__brief__ = "显示机器人的状态"
uptime.__doc__ = '''\
Uptime 在重启系统（含崩溃自动重启）时归零
Bot Uptime 在重启机器人（含重启系统）时归零'''
def format_seconds(seconds: int) -> str:
  minutes, seconds = divmod(seconds, 60)
  hours,   minutes = divmod(minutes, 60)
  days,    hours   = divmod(hours, 24)
  segments = []
  if days:
    segments.append(f"{int(days)} {'day' if days == 1 else 'days'}")
  if hours:
    segments.append(f"{int(hours)} {'hour' if hours == 1 else 'hours'}")
  if minutes or not len(segments):
    segments.append(f"{int(minutes)} {'minute' if minutes == 1 else 'minutes'}")
  return ", ".join(segments)

@uptime.handle()
async def handle_uptime():
  cur_time = time.time()
  uptime_str = format_seconds(cur_time - psutil.boot_time())
  cpu_util = round(psutil.cpu_percent())
  cpu_freq = round(psutil.cpu_freq().current * 1024)
  cpu_temp = round(psutil.sensors_temperatures()['k10temp'][0].current)
  cpu_str = f"{cpu_util}% {cpu_freq}MHz {cpu_temp}°C"
  proc = await asyncio.create_subprocess_exec(gpuload, "{load}% {clock}MHz {temp}°C (VRAM: {memload}%)", stdout=subprocess.PIPE)
  gpu_str = (await proc.stdout.read()).decode().rstrip()
  ram_info = psutil.virtual_memory()
  ram_str = f"{round(ram_info.used / MEGA)}MiB / {round(ram_info.total / MEGA)}MiB ({round(ram_info.percent)}%)"
  swap_info = psutil.swap_memory()
  swap_str = f"{round(swap_info.used / MEGA)}MiB / {round(swap_info.total / MEGA)}MiB ({round(swap_info.percent)}%)"
  botuptime_str = format_seconds(cur_time - bot_start_time)
  im = Image.open(os.path.join(plugin_dir, "template.png"))
  draw = ImageDraw.Draw(im)
  draw.text((441, 80), kernel_str, color, font)
  draw.text((441, 100), uptime_str, color, font)
  draw.text((468, 140), cpu_str, color, font)
  draw.text((468, 180), gpu_str, color, font)
  draw.text((414, 200), ram_str, color, font)
  draw.text((423, 220), swap_str, color, font)
  draw.text((441, 240), python_str, color, font)
  draw.text((450, 260), nonebot.__version__, color, font)
  draw.text((468, 280), idhagnbot_str, color, font)
  draw.text((477, 300), botuptime_str, color, font)
  io = BytesIO()
  im.save(io, "png")
  await uptime.send(MessageSegment.image(io))