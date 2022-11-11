import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, context, imutil, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--name", "-n", metavar="名字", help=(
  "自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称"
))
matcher = (
  command.CommandBuilder("meme_pic.friend", "交朋友")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)
  target, target_id = target_task.result()
  if args.name is not None:
    name = args.name
  elif target_id is not None:
    name = await context.get_card_or_name(bot, event, target_id)
  else:
    await matcher.finish("请使用 --name 指定名字")

  def make() -> MessageSegment:
    nonlocal target
    target = target.resize((1000, 1000), imutil.scale_resample())
    im = Image.new("RGB", target.size, (255, 255, 255))
    im.paste(target, mask=target)
    overlay = Image.open(DIR / "template.png")
    target1 = im.resize((250, 250), imutil.scale_resample()).rotate(9, imutil.resample(), True)
    target2 = im.resize((55, 55), imutil.scale_resample()).rotate(9, imutil.resample())
    im.paste(target1, (im.width - 257, im.height - 155))
    im.paste(target2, (im.width - 160, im.height - 273))
    im.paste(overlay, (im.width - overlay.width, im.height - overlay.height), overlay)
    text_im = textutil.render(
      name, "sans", 20, color=(255, 255, 255), box=230, ellipsize=textutil.ELLIPSIZE_END
    )
    text_im = ImageOps.pad(text_im, (230, text_im.height), centering=(0, 0))
    text_im = text_im.rotate(9, imutil.resample(), True)
    im.paste(text_im, (im.width - 281, im.height - 345), text_im)
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
