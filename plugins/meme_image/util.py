from dataclasses import dataclass
import random
from util.config import BaseConfig
from util import context, account_aliases
from typing import Callable, TypeVar, Awaitable
from PIL import Image, ImageDraw, ImageFilter
from io import BytesIO
from aiohttp import ClientSession
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.params import CommandArg
from nonebot.log import logger
import nonebot
import re
import os

class Config(BaseConfig):
  __file__ = "meme_image"
  static_format: str = "png"
  animated_format: str = "gif"

CONFIG = Config.load()

exports = nonebot.export()
resources_dir = os.path.abspath("resources/meme_image") + os.sep

@exports
@dataclass
class Animated:
  frames: list[Image.Image]
  duration: int

async def get_avatar(http: ClientSession, uid: int) -> Image.Image:
  # s 有 100, 160, 640 分别对应最大 3 个尺寸（可以小）和 0 对应原图（不能不填）
  response = await http.get(f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=0")
  return Image.open(BytesIO(await response.read())).convert("RGBA")

async def get_image(http: ClientSession, url: str) -> Image.Image:
  response = await http.get(url)
  return Image.open(BytesIO(await response.read())).convert("RGBA")

IMAGE_TYPES = {
  "image": "图片链接或用户",
  "user": "用户",
  "image_self": "图片链接或用户（省略将使用执行者）",
  "user_self": "用户（省略将使用执行者）",
}
HTTP_RE = re.compile("^https?://")

TFactory = TypeVar("TFactory", bound=Callable[..., Awaitable[Image.Image | Animated]])
@exports
def register(names: str | list[str], brief: str = "", usage: str = "", *, category: str = "", user: bool = False, has_self: bool = False, swap: bool = False, contexts: int | list[int] = []) -> Callable[[TFactory], TFactory]:
  if not isinstance(names, list):
    names = [names]
  max_args = 2 if has_self else 1
  def decorator(factory: TFactory) -> TFactory:
    async def handler(bot: Bot, event: Event, msg = CommandArg()):
      args: list[str | int] = []
      text = ""
      for i in msg:
        if i.type == "text":
          text += i.data["text"]
        else:
          args.extend(text.split())
          text = ""
          if i.type == "at":
            args.append(i.data["qq"])
      args.extend(text.split())
      if len(args) > max_args:
        await matcher.finish(f"最多只能有 {max_args} 个参数")
      call_args = []
      all_errors = []

      async def add_args(is_self: bool):
        pos = 0 if is_self else -1
        if len(args) < (2 if is_self else 1):
          uid = event.user_id if is_self != swap else event.self_id
        elif not user and HTTP_RE.match(args[pos]):
          try:
            call_args.append(await get_image(http, args[pos]))
          except:
            all_errors.append(f"下载 {args[pos]} 失败")
          return
        elif not user and args[pos].startswith("file://"):
          path = os.path.abspath(args[pos][7:])
          if not path.startswith(resources_dir):
            all_errors.append("你以为你能逃到资源目录外面吗？")
          elif os.path.isfile(path):
            call_args.append(Image.open(path))
          else:
            all_errors.append("路径不存在或不是文件")
          return
        else:
          try:
            uid = int(args[pos])
          except:
            errors, uid = await account_aliases.match_uid(bot, event, args[pos])
            all_errors.extend(errors)
        if user:
          call_args.append(uid)
        try:
          call_args.append(await get_avatar(http, uid))
        except:
          all_errors.append(f"下载 {uid} 的头像失败")

      async with ClientSession() as http:
        if has_self:
          await add_args(True)
        await add_args(False)
      if len(all_errors):
        await matcher.finish("\n".join(all_errors))
      f = BytesIO()
      im = await factory(*call_args)
      if isinstance(im, Animated):
        im.frames[0].save(f, CONFIG.animated_format, append_images=im.frames[1:], save_all=True, duration=im.duration, loop=0)
      else:
        im.save(f, CONFIG.static_format)
      await matcher.finish(MessageSegment.image(f))
    matcher = nonebot.on_command(names[0], context.in_group_rule(*contexts), set(names[1:]), handlers=[handler])
    matcher.__cmd__ = names
    matcher.__cat__ = category
    matcher.__brief__ = brief
    matcher.__doc__ = usage
    matcher.__ctx__ = contexts
    return factory
  return decorator

@exports
def circle(img: Image.Image) -> Image.Image:
  mask = Image.new('L', img.size, 0)
  ImageDraw.Draw(mask).ellipse((1, 1, img.size[0] - 2, img.size[1] - 2), 255)
  mask = mask.filter(ImageFilter.GaussianBlur(0))
  img.putalpha(mask)
  return img
