import asyncio
import os
import socket
from typing import Callable, Optional, Tuple

import aiohttp
from aiohttp import web
from nonebot.adapters.onebot.v11 import MessageSegment
from pydantic import BaseModel

from util import command, configs, misc


class Config(BaseModel):
  timeout: float = 15
  warn: bool = True
  dog_gif_only: bool = False
  proxy: Optional[str] = None


CONFIG = configs.SharedConfig("catdog", Config)
WARN_STR = "（翻译：API在国外，该命令缓慢或出错是正常现象）"
CAT_API = "https://aws.random.cat/meow"
CAT_GIF_API = "https://edgecats.net"
DOG_API = "https://random.dog/woof.json?filter=gif,mp4,webm"
DOG_GIF_API = "https://random.dog/woof.json?include=gif"


def usage_factory(prefix: str) -> Callable[[], str]:
  def get_usage() -> str:
    usage = prefix
    if CONFIG().warn:
      usage += WARN_STR
    return usage
  return get_usage


cat = (
  command.CommandBuilder("catdog.cat", "喵", "喵喵", "meow")
  .brief("喵喵喵？喵喵。")
  .usage(usage_factory("喵，喵喵。"))
  .build()
)
@cat.handle()
async def handle_cat() -> None:
  async def fetch() -> bytes:
    nonlocal url
    http = misc.http()
    try:
      async with http.get(CAT_API, proxy=config.proxy) as response:
        url = (await response.json())["file"]
      async with http.get(url, proxy=config.proxy) as response:
        return await response.read()
    except aiohttp.ClientProxyConnectionError as e:
      raise misc.AggregateError("代理连接失败") from e
    except aiohttp.ClientError as e:
      raise misc.AggregateError("下载出错：" + url) from e

  config = CONFIG()
  url = "获取URL出错"
  try:
    img = await asyncio.wait_for(fetch(), config.timeout)
  except asyncio.TimeoutError:
    await dog.finish("下载超时：" + url)
  except misc.AggregateError as e:
    await dog.finish("\n".join(e))
  await dog.finish(MessageSegment.image(img))


cat_gif = (
  command.CommandBuilder("catdog.cat_gif", "喵呜")
  .brief("喵呜！喵——呜——")
  .usage(usage_factory("呼噜呼噜，喵呜。"))
  .build()
)
@cat_gif.handle()
async def handle_cat_gif() -> None:
  async def fetch() -> bytes:
    http = misc.http()
    try:
      async with http.get(CAT_GIF_API, proxy=config.proxy) as response:
        return await response.read()
    except aiohttp.ClientProxyConnectionError as e:
      raise misc.AggregateError("代理连接失败") from e
    except aiohttp.ClientError as e:
      raise misc.AggregateError("下载出错") from e

  config = CONFIG()
  try:
    img = await asyncio.wait_for(fetch(), config.timeout)
  except asyncio.TimeoutError:
    await dog.finish("下载超时")
  except misc.AggregateError as e:
    await dog.finish("\n".join(e))
  await dog.finish(MessageSegment.image(img))


dog = (
  command.CommandBuilder("catdog.dog", "汪", "汪汪", "woof")
  .brief("汪？汪汪，汪汪汪！")
  .usage(usage_factory("汪汪，汪汪。"))
  .build()
)
@dog.handle()
async def handle_dog() -> None:
  async def fetch() -> bytes:
    nonlocal url
    http = misc.http()
    try:
      async with http.get(DOG_API, proxy=config.proxy) as response:
        url = (await response.json())["url"]
      async with http.get(url, proxy=config.proxy) as response:
        return await response.read()
    except aiohttp.ClientProxyConnectionError as e:
      raise misc.AggregateError("代理连接失败") from e
    except aiohttp.ClientError as e:
      raise misc.AggregateError("下载出错：" + url) from e

  config = CONFIG()
  url = "获取URL出错"
  try:
    img = await asyncio.wait_for(fetch(), config.timeout)
  except asyncio.TimeoutError:
    await dog.finish("下载超时：" + url)
  except misc.AggregateError as e:
    await dog.finish("\n".join(e))
  await dog.finish(MessageSegment.image(img))


dog_gif = (
  command.CommandBuilder("catdog.dog_gif", "汪嗷")
  .brief("汪，汪，汪嗷～")
  .usage(usage_factory("汪汪……呜嗷！"))
  .build()
)
@dog_gif.handle()
async def handle_dog_gif() -> None:
  async def fetch() -> Tuple[str, str, bytes]:
    nonlocal url
    http = misc.http()
    api = DOG_GIF_API
    if not config.dog_gif_only:
      api += ",mp4,webm"
    try:
      async with http.get(api, proxy=config.proxy) as response:
        url = (await response.json())["url"]
      async with http.get(url, proxy=config.proxy) as response:
        ext = os.path.splitext(url.lower())[1]
        mime = response.content_type
        img = await response.read()
        return (ext, mime, img)
    except aiohttp.ClientProxyConnectionError as e:
      raise misc.AggregateError("代理连接失败") from e
    except aiohttp.ClientError as e:
      raise misc.AggregateError("下载出错：") from e

  config = CONFIG()
  url = "获取URL出错"
  try:
    ext, mime, img = await asyncio.wait_for(fetch(), config.timeout)
  except asyncio.TimeoutError:
    await dog_gif.finish("下载超时：" + url)
  except misc.AggregateError as e:
    await dog_gif.finish("\n".join(e))
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
    await dog_gif.finish(MessageSegment.video(f"http://127.0.0.1:{port}/video{ext}"))
  finally:
    await site.stop()
