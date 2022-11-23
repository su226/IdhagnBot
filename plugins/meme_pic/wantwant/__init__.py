from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
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
  command.CommandBuilder("meme_pic.wantwant", "旺仔", "旺旺")
  .category("meme_pic")
  .brief("李子明的最爱")
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
    im = Image.open(DIR / "template.png")
    text_im = textutil.render(name, "sans heavy", 80, color=(255, 255, 255))
    if text_im.width > 355:
      text_im = text_im.resize((355, text_im.height), imutil.scale_resample())
    im.paste(text_im, (157, 51), text_im)
    target = target.resize((226, 226), imutil.scale_resample())
    im.paste(target, (136, 182), target)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
