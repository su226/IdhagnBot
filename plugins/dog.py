from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientProxyConnectionError
from aiohttp import web
from util.config import BaseConfig
from nonebot.adapters.onebot.v11 import MessageSegment
import nonebot
import socket
import asyncio
import os

class Config(BaseConfig):
  __file__ = "dog"
  timeout: float = 15
  warn: bool = True
  dog_gif_only: bool = False
  proxy: str | None = None

CONFIG = Config.load()
WARN_STR = "（翻译：API在国外，该命令缓慢或出错是正常现象）" if CONFIG.warn else ""

CAT_API = "https://aws.random.cat/meow"
cat = nonebot.on_command("喵", aliases={"喵喵", "meow"})
cat.__cmd__ = ["喵", "喵喵", "meow"]
cat.__brief__ = "喵喵喵？喵喵。"
cat.__doc__ = "喵，喵喵。" + WARN_STR
@cat.handle()
async def handle_cat():
  async with ClientSession() as http:
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
cat_gif = nonebot.on_command("喵呜")
cat_gif.__cmd__ = "喵呜"
cat_gif.__brief__ = "喵呜！喵——呜——"
cat_gif.__doc__ = "呼噜呼噜，喵呜。" + WARN_STR
@cat_gif.handle()
async def handle_cat_gif():
  async with ClientSession() as http:
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
dog = nonebot.on_command("汪", aliases={"汪汪", "woof"})
dog.__cmd__ = ["汪", "汪汪", "woof"]
dog.__brief__ = "汪？汪汪，汪汪汪！"
dog.__doc__ = "汪汪，汪汪。" + WARN_STR
@dog.handle()
async def handle_dog():
  async with ClientSession() as http:
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
dog_gif = nonebot.on_command("汪嗷")
dog_gif.__cmd__ = "汪嗷"
dog_gif.__brief__ = "汪，汪，汪嗷～"
dog_gif.__doc__ = "汪汪……呜嗷！" + WARN_STR
@dog_gif.handle()
async def handle_dog_gif():
  async with ClientSession() as http:
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
  async def handler(_: web.Request):
    return web.Response(body=vid, content_type=mime)
  server = web.Server(handler)
  runner = web.ServerRunner(server)
  await runner.setup()
  with socket.socket() as s:
    s.bind(("", 0))
    port = s.getsockname()[1]
  site = web.TCPSite(runner, "localhost", port)
  await site.start()
  await dog_gif.send(MessageSegment.video(f"http://127.0.0.1:{port}/video{ext}"))
  await site.stop()
