import socket
import asyncio
import os

from aiohttp.client_exceptions import ClientProxyConnectionError
from aiohttp import web
from nonebot.adapters.onebot.v11 import MessageSegment
import aiohttp

from util import command
from util.config import BaseConfig

class Config(BaseConfig):
  __file__ = "dog"
  timeout: float = 15
  warn: bool = True
  dog_gif_only: bool = False
  proxy: str | None = None

CONFIG = Config.load()
WARN_STR = "（翻译：API在国外，该命令缓慢或出错是正常现象）" if CONFIG.warn else ""

CAT_API = "https://aws.random.cat/meow"
cat = (command.CommandBuilder("dog.cat", "喵", "喵喵", "meow")
  .brief("喵喵喵？喵喵。")
  .usage("喵，喵喵。" + WARN_STR)
  .build())
@cat.handle()
async def handle_cat():
  async with aiohttp.ClientSession() as http:
    url = "获取URL出错"
    try:
      response = await http.get(CAT_API, proxy=CONFIG.proxy)
      url = (await response.json())["file"]
      response = await http.get(url, proxy=CONFIG.proxy)
      img = await asyncio.wait_for(response.read(), CONFIG.timeout)
    except ClientProxyConnectionError:
      await cat.finish("代理连接失败")
    except asyncio.TimeoutError:
      await cat.finish("下载超时：" + url)
    except:
      await cat.finish("下载出错：" + url)
  await cat.finish(MessageSegment.image(img))

CAT_GIF_API = "https://edgecats.net"
cat_gif = (command.CommandBuilder("dog.cat_gif", "喵呜")
  .brief("喵呜！喵——呜——")
  .usage("呼噜呼噜，喵呜。" + WARN_STR)
  .build())
@cat_gif.handle()
async def handle_cat_gif():
  async with aiohttp.ClientSession() as http:
    try:
      response = await http.get(CAT_GIF_API, proxy=CONFIG.proxy)
      data = await asyncio.wait_for(response.read(), CONFIG.timeout)
    except ClientProxyConnectionError:
      await cat_gif.finish("代理连接失败")
    except asyncio.TimeoutError:
      await cat_gif.finish("下载超时")
    except:
      await cat_gif.finish("下载出错")
  await cat_gif.finish(MessageSegment.image(data))

DOG_API = "https://random.dog/woof.json?filter=gif,mp4,webm"
dog = (command.CommandBuilder("dog.dog", "汪", "汪汪", "woof")
  .brief("汪？汪汪，汪汪汪！")
  .usage("汪汪，汪汪。" + WARN_STR)
  .build())
@dog.handle()
async def handle_dog():
  async with aiohttp.ClientSession() as http:
    url = "获取URL出错"
    try:
      response = await http.get(DOG_API, proxy=CONFIG.proxy)
      url = (await response.json())["url"]
      response = await http.get(url, proxy=CONFIG.proxy)
      img = await asyncio.wait_for(response.read(), CONFIG.timeout)
    except ClientProxyConnectionError:
      await dog.finish("代理连接失败")
    except asyncio.TimeoutError:
      await dog.finish("下载超时：" + url)
    except:
      await dog.finish("下载出错：" + url)
  await dog.finish(MessageSegment.image(img))

DOG_GIF_API = "https://random.dog/woof.json?include=gif"
if not CONFIG.dog_gif_only:
  DOG_GIF_API += ",mp4,webm"
dog_gif = (command.CommandBuilder("dog.dog_gif", "汪嗷")
  .brief("汪，汪，汪嗷～")
  .usage("汪汪……呜嗷！" + WARN_STR)
  .build())
@dog_gif.handle()
async def handle_dog_gif():
  async with aiohttp.ClientSession() as http:
    url = "获取URL出错"
    from loguru import logger
    try:
      response = await http.get(DOG_GIF_API, proxy=CONFIG.proxy)
      url = (await response.json())["url"]
      response = await http.get(url, proxy=CONFIG.proxy)
      mime = response.content_type
      logger.info("start download")
      img = await asyncio.wait_for(response.read(), CONFIG.timeout)
      logger.info("download finish")
    except ClientProxyConnectionError:
      await dog_gif.finish("代理连接失败")
    except asyncio.TimeoutError:
      logger.info("download timeout")
      await dog_gif.finish("下载超时：" + url)
    except:
      await dog_gif.finish("下载出错：" + url)
  ext = os.path.splitext(url.lower())[1]
  if ext in (".mp4", ".webm"):
    await send_video(ext, mime, img)
    await dog_gif.finish()
  await dog_gif.finish(MessageSegment.image(img))

# go-cqhttp v1.0.0-rc1 使用 file 链接发视频会出错，只能用这种方法替代
async def send_video(ext: str, mime: str, vid: bytes):
  async def handler(_: web.BaseRequest):
    return web.Response(body=vid, content_type=mime)
  server = web.Server(handler)
  runner = web.ServerRunner(server)
  await runner.setup()
  with socket.socket() as s:
    s.bind(("", 0))
    port = s.getsockname()[1]
  site = web.TCPSite(runner, "localhost", port)
  await site.start()
  try:
    await dog_gif.send(MessageSegment.video(f"http://127.0.0.1:{port}/video{ext}"))
  finally:
    await site.stop()
