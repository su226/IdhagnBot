import asyncio
from argparse import Namespace
from io import BytesIO
from typing import Any, Optional

import nonebot
from meme_generator import (
  BooleanOption, DeserializeError, FloatOption, Image as MemeImage, ImageAssetMissing,
  ImageDecodeError, ImageEncodeError, ImageNumberMismatch, Meme, MemeFeedback, StringOption,
  TextNumberMismatch, TextOverLength, get_memes,
)
from meme_generator.resources import check_resources_in_background
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, misc, user_aliases

driver = nonebot.get_driver()


@driver.on_startup
def _() -> None:
  check_resources_in_background()


async def get_avatar_and_info_from_pattern(
  g: user_aliases.AvatarGetter, pattern: str,
) -> tuple[Image.Image, Optional[dict[str, Any]]]:
  image, user = await g.get(pattern, user_aliases.DefaultType.SOURCE)
  return image, await g.bot.get_stranger_info(user_id=user) if user is not None else None


async def get_avatar_and_info_from_id(bot: Bot, uid: int) -> tuple[Image.Image, dict[str, Any]]:
  return await user_aliases.get_avatar(uid), await bot.get_stranger_info(user_id=uid)


async def check_image_count(meme: Meme, count: int) -> None:
  if not (meme.info.params.min_images <= count <= meme.info.params.max_images):
    raise misc.AggregateError(
      f"输入图片数量不符，图片数量应为 {meme.info.params.min_images}" + (
        f" ~ {meme.info.params.max_images}"
        if meme.info.params.max_images > meme.info.params.min_images
        else ""
      ),
    )


async def check_text_count(meme: Meme, count: int) -> None:
  if not (meme.info.params.min_texts <= count <= meme.info.params.max_texts):
    raise misc.AggregateError(
      f"输入文字数量不符，文字数量应为 {meme.info.params.min_texts}" + (
        f" ~ {meme.info.params.max_texts}"
        if meme.info.params.max_texts > meme.info.params.min_texts
        else ""
      ),
    )


def create_matcher(meme: Meme) -> None:
  parser = ArgumentParser(add_help=False)
  parser.add_argument("meme_params", nargs="*")
  for option in meme.info.params.options:
    names = []
    if option.parser_flags.short:
      names.append(f"-{option.name[0]}")
    names.extend(f"-{x}" for x in option.parser_flags.short_aliases)
    if option.parser_flags.long:
      names.append(f"--{option.name}")
    names.extend(f"--{x}" for x in option.parser_flags.long_aliases)
    if isinstance(option, BooleanOption):
      if option.default is None:
        print(meme, option)
      parser.add_argument(
        *names,
        action="store_false" if option.default else "store_true",
        dest=option.name,
        help=option.description,
      )
    elif isinstance(option, StringOption):
      parser.add_argument(
        *names,
        default=option.default,
        choices=option.choices,
        help=option.description,
        dest=option.name,
      )
    else:
      parser.add_argument(
        *names,
        default=option.default,
        type=(
          misc.range_float(option.minimum, option.maximum)
          if isinstance(option, FloatOption) else
          misc.range_int(option.minimum, option.maximum) 
        ),
        help=option.description,
        dest=option.name,
      )

  matcher = (
    command.CommandBuilder(f"memes.{meme.key}", *meme.info.keywords)
    .category("memes")
    .shell(parser)
    .build()
  )
  @matcher.handle()
  async def _(
    bot: Bot,
    event: MessageEvent,
    ns: Namespace = ShellCommandArgs(),
  ):
    tasks: list[asyncio.Task[tuple[Image.Image, Optional[dict[str, Any]]]]] = []
    texts: list[str] = []
    names: list[str] = []

    async with user_aliases.AvatarGetter(bot, event) as g:
      for arg in ns.meme_params:
        if (
          user_aliases.AT_RE.match(arg)
          or user_aliases.IMAGE_RE.match(arg)
          or user_aliases.LINK_RE.match(arg)
          or arg.startswith("@")
          or arg in {
            "-", "这个", "?", "那个", "它", "~", "自己", "我", "0", "机器人", "bot", "你", "!",
            "他", "她", "牠", "祂",
          }
        ):
          tasks.append(g.submit(get_avatar_and_info_from_pattern(g, arg.removeprefix("@"))))
        elif arg.startswith("#"):
          names.append(arg[1:])
        elif arg:
          texts.append(arg)

      if meme.info.params.min_images == 2:
        if len(tasks) == 1:
          # 当所需图片数为 2 且已指定图片数为 1 时，使用发送者的头像作为第一张图
          tasks.insert(0, g.submit(get_avatar_and_info_from_id(bot, event.user_id)))
        elif len(tasks) == 0:
          # 当所需图片数为 2 且没有已指定图片时，使用发送者和机器人的头像
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.user_id)))
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.self_id)))
      elif meme.info.params.min_images == 1:
        if len(tasks) == 0:
          # 当所需图片数为 1 且没有已指定图片时，使用发送者的头像
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.user_id)))

      if meme.info.params.min_texts > 0 and len(texts) == 0:
        # 当所需文字数 > 0 且没有输入文字时，使用默认文字
        texts = meme.info.params.default_texts

      g.submit(check_image_count(meme, len(tasks)))
      g.submit(check_text_count(meme, len(texts)))

    def make() -> MessageSegment:
      images: list[MemeImage] = []
      for i, task in enumerate(tasks):
        image, user = task.result()
        f = BytesIO()
        image.save(f, "png")
        name_override = names[i] if i < len(names) else ""
        if name_override:
          images.append(MemeImage(name_override, f.getvalue()))
        elif user:
          images.append(MemeImage(user["nickname"], f.getvalue()))
        else:
          images.append(MemeImage("", f.getvalue()))
      options = {k: v for k, v in ns.__dict__.items() if k != "meme_params" and v is not None}
      result = meme.generate(images, texts, options)
      if isinstance(result, ImageDecodeError):
        return MessageSegment.text(f"图片解码出错：{result.error}")
      elif isinstance(result, ImageEncodeError):
        return MessageSegment.text(f"图片编码出错：{result.error}")
      elif isinstance(result, ImageAssetMissing):
        return MessageSegment.text(f"缺少图片资源：{result.path}")
      elif isinstance(result, DeserializeError):
        return MessageSegment.text(f"表情选项解析出错：{result.error}")
      elif isinstance(result, ImageNumberMismatch):
        num = (
          f"{result.min} ~ {result.max}"
          if result.min != result.max
          else str(result.min)
        )
        return MessageSegment.text(f"图片数量不符，应为 {num}，实际传入 {result.actual}")
      elif isinstance(result, TextNumberMismatch):
        num = (
          f"{result.min} ~ {result.max}"
          if result.min != result.max
          else str(result.min)
        )
        return MessageSegment.text(f"文字数量不符，应为 {num}，实际传入 {result.actual}")
      elif isinstance(result, TextOverLength):
        repr = result.text[:10] + "..." if len(result.text) > 10 else result.text
        return MessageSegment.text(f"文字过长：{repr}")
      elif isinstance(result, MemeFeedback):
        return MessageSegment.text(result.feedback)
      return MessageSegment.image(result)

    await matcher.finish(await misc.to_thread(make))


for meme in get_memes():
  create_matcher(meme)
