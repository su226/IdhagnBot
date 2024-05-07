from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter, DefaultType

DIR = Path(__file__).resolve().parent
AVATAR_TRANSFORM = (1.0116, -0.0598, 0, -0.0453, 1.0905, 0, 0, 0.0004)
NAME_TRANSFORM = (1, -0.125, 0, 0, 1, 0)


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument(
  "--name", "-n", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称",
)
matcher = (
  command.CommandBuilder("meme_pic.police", "警察", "police")
  .category("meme_pic")
  .brief("低调使用小心进局子")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, DefaultType.TARGET)
  target, user = target_task.result()
  if args.name is not None:
    name = args.name
  elif user is not None:
    name = await context.get_card_or_name(bot, event, user)
  else:
    await matcher.finish("请使用 --name 指定名字")

  def make() -> MessageSegment:
    nonlocal target
    large = target.resize((460, 460), imutil.scale_resample()).rotate(-17, imutil.resample(), True)
    pre_small = target.resize((118, 118), imutil.scale_resample())
    small = Image.new("RGBA", (120, 120))
    small.paste(pre_small, (1, 1), pre_small)
    small = small.transform(
      (200, 200), Image.Transform.PERSPECTIVE, AVATAR_TRANSFORM, imutil.resample(),
    )
    im = Image.new("RGB", (600, 600), (255, 255, 255))
    im.paste(large, (84, 114), large)
    template = Image.open(DIR / "template.png")
    im.paste(template, (0, 0), template)
    im.paste(small, (82, 409), small)
    text_im = textutil.render(name, "sans", 16)
    if text_im.width > 120:
      text_im = text_im.resize((120, 24), imutil.scale_resample())
    else:
      text_im = ImageOps.pad(text_im, (120, 24), imutil.scale_resample())
    text_im = text_im.transform(
      (123, 24), Image.Transform.AFFINE, NAME_TRANSFORM, imutil.resample(),
    )
    im.paste(text_im, (90, 534), text_im)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
