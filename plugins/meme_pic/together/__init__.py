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
parser.add_argument("--text", "-t", default="", metavar="文本", help=(
  "自定义内容，默认为“一起玩[用户名]吧！”"
))
matcher = (
  command.CommandBuilder("meme_pic.togeter", "一起玩")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id)
  target, user = target_task.result()
  if args.text:
    content = args.text
  elif user:
    name = await context.get_card_or_name(bot, event, user)
    content = f"一起玩{name}吧！"
  else:
    await matcher.finish("请使用 --text 指定文本")

  def make() -> MessageSegment:
    nonlocal target
    im = Image.open(DIR / "template.png").convert("RGB")
    target = target.resize((63, 63), imutil.scale_resample())
    im.paste(target, (132, 36), target)

    text_im = textutil.render(content, "sans", 32)
    text_im = imutil.contain_down(text_im, 180, 50)
    imutil.paste(im, text_im, (100, 165), anchor="mm")
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
