from argparse import Namespace

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image

from util import command, context, imutil, misc, textutil
from util.user_aliases import AvatarGetter

parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--name", "-n", metavar="名字", help=(
  "自定义名字，对于图片链接默认为“男同”，对于QQ用户默认使用昵称"
))
matcher = (
  command.CommandBuilder("meme_pic.follow", "关注")
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
    name = "男同"

  def make() -> MessageSegment:
    nonlocal target
    target = target.resize((200, 200), imutil.scale_resample())
    imutil.circle(target)
    text_im = textutil.render(name, "sans", 60)
    text2_im = textutil.render("关注了你", "sans", 60, color=(127, 127, 127))
    text_width = max(text_im.width, text2_im.width)
    text_height = max(text_im.height + 10 + text2_im.height, target.height)
    im = Image.new("RGB", (150 + target.width + text_width, 100 + text_height), (255, 255, 255))
    im.paste(target, (50, 50), target)
    im.paste(text_im, (target.width + 100, 50), text_im)
    im.paste(text2_im, (target.width + 100, 60 + text_im.height), text2_im)
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
