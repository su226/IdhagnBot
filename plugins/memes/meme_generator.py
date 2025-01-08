import asyncio
from argparse import Namespace
from io import BytesIO
from typing import Any, Optional

import nonebot
from meme_generator import Meme, get_memes
from meme_generator.download import check_resources
from meme_generator.meme import UserInfo
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, misc, user_aliases

driver = nonebot.get_driver()


@driver.on_startup
async def _() -> None:
  asyncio.create_task(check_resources())


async def get_avatar_and_info_from_pattern(
  g: user_aliases.AvatarGetter, pattern: str,
) -> tuple[Image.Image, Optional[dict[str, Any]]]:
  image, user = await g.get(pattern, user_aliases.DefaultType.SOURCE)
  return image, await g.bot.get_stranger_info(user_id=user) if user is not None else None


async def get_avatar_and_info_from_id(bot: Bot, uid: int) -> tuple[Image.Image, dict[str, Any]]:
  return await user_aliases.get_avatar(uid), await bot.get_stranger_info(user_id=uid)


async def check_image_count(meme: Meme, count: int) -> None:
  if not (meme.params_type.min_images <= count <= meme.params_type.max_images):
    raise misc.AggregateError(
      f"输入图片数量不符，图片数量应为 {meme.params_type.min_images}" + (
        f" ~ {meme.params_type.max_images}"
        if meme.params_type.max_images > meme.params_type.min_images
        else ""
      ),
    )


async def check_text_count(meme: Meme, count: int) -> None:
  if not (meme.params_type.min_texts <= count <= meme.params_type.max_texts):
    raise misc.AggregateError(
      f"输入文字数量不符，文字数量应为 {meme.params_type.min_texts}" + (
        f" ~ {meme.params_type.max_texts}"
        if meme.params_type.max_texts > meme.params_type.min_texts
        else ""
      ),
    )


def create_matcher(meme: Meme) -> None:
  parser = ArgumentParser(add_help=False)
  parser.add_argument("meme_params", nargs="*")
  if meme.params_type.args_type:
    for option in meme.params_type.args_type.parser_options:
      if option.args:
        parser.add_argument(
          *(name for name in option.names if name.startswith("-")),
          dest=option.args[0].name,
          default=option.args[0].default,
          help=option.help_text,
        )
      else:
        parser.add_argument(
          *(name for name in option.names if name.startswith("-")),
          dest=option.dest,
          default=option.default,
          action="store_const",
          const=option.action.value if option.action else None,
          help=option.help_text,
        )

  matcher = (
    command.CommandBuilder(f"memes.{meme.key}", *meme.keywords)
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
          tasks.append(g.submit(get_avatar_and_info_from_pattern(g, arg)))
        elif arg:
          texts.append(arg)

      if meme.params_type.min_images == 2:
        if len(tasks) == 1:
          # 当所需图片数为 2 且已指定图片数为 1 时，使用发送者的头像作为第一张图
          tasks.insert(0, g.submit(get_avatar_and_info_from_id(bot, event.user_id)))
        elif len(tasks) == 0:
          # 当所需图片数为 2 且没有已指定图片时，使用发送者和机器人的头像
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.user_id)))
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.self_id)))
      elif meme.params_type.min_images == 1:
        if len(tasks) == 0:
          # 当所需图片数为 1 且没有已指定图片时，使用发送者的头像
          tasks.append(g.submit(get_avatar_and_info_from_id(bot, event.user_id)))

      if meme.params_type.min_texts > 0 and len(texts) == 0:
        # 当所需文字数 > 0 且没有输入文字时，使用默认文字
        texts = meme.params_type.default_texts

      g.submit(check_image_count(meme, len(tasks)))
      g.submit(check_text_count(meme, len(texts)))

    def make() -> MessageSegment:
      images_data: list[BytesIO] = []
      users: list[UserInfo] = []
      for task in tasks:
        image, user = task.result()
        f = BytesIO()
        image.save(f, "png")
        images_data.append(f)
        if user:
          users.append(UserInfo(name=user["nickname"], gender=user["sex"]))
      args = {k: v for k, v in ns.__dict__.items() if k != "meme_params"}
      args["user_infos"] = users
      return MessageSegment.image(meme(images=images_data, texts=texts, args=args))

    await matcher.finish(await misc.to_thread(make))


for meme in get_memes():
  create_matcher(meme)
