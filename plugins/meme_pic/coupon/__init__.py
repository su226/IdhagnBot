import asyncio
from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--text", "-t", metavar="文本", help=(
  "自定义内容，默认为“xxx陪睡劵（永久有效）”"
))
matcher = (
  command.CommandBuilder("meme_pic.coupon", "兑换劵")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)
  target, target_id = target_task.result()

  if args.text:
    content = args.text
  elif target_id:
    name = await context.get_card_or_name(bot, event, target_id)
    content = f"{name}陪睡劵\n（永久有效）"
  else:
    await matcher.finish("请用 --text 指定文本")

  def make() -> MessageSegment:
    im = Image.open(DIR / "template.png")
    nonlocal target
    target = target.resize((60, 60), imutil.scale_resample()).rotate(22, imutil.resample())
    imutil.circle(target)
    text_im = textutil.render(content, "sans", 30, align="m")
    text_im = imutil.center_pad(text_im, 220, 100)
    text_im = text_im.rotate(22, imutil.resample(), True)
    im.paste(target, (63, 198), target)
    im.paste(text_im, (118, 77), text_im)
    return imutil.to_segment(im)

  await matcher.finish(await asyncio.to_thread(make))
