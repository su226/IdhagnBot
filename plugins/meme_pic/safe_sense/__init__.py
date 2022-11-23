from argparse import Namespace
from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.params import ShellCommandArgs
from nonebot.rule import ArgumentParser
from PIL import Image, ImageOps

from util import command, imutil, misc, textutil
from util.user_aliases import AvatarGetter

DIR = Path(__file__).resolve().parent
GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}


parser = ArgumentParser(add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help=(
  "可使用@、QQ号、昵称、群名片或图片链接"
))
parser.add_argument("--gender", "-g", choices=GENDERS, metavar="性别", help=(
  "自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，可以是“male”（他）、"
  "“female”（她）、“unknown”（它）、“animal”（牠）、“god”（祂）"
))
matcher = (
  command.CommandBuilder("meme_pic.safe_sense", "安全感")
  .category("meme_pic")
  .shell(parser)
  .build()
)
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()) -> None:
  async with AvatarGetter(bot, event) as g:
    target_task = g(args.target, event.self_id, crop=False)
  target, user = target_task.result()
  gender = args.gender
  if gender is None:
    if user is not None:
      info = await bot.get_stranger_info(user_id=user)
      gender = info["sex"]
    else:
      gender = "unknown"

  def make() -> MessageSegment:
    nonlocal target
    target = ImageOps.fit(target, (215, 343), imutil.scale_resample())
    im = Image.open(DIR / "template.png")
    im.paste(target, (215, 135), target)
    content = f"你给我的安全感\n远不及{GENDERS[gender]}的万分之一"
    textutil.paste(im, (im.width // 2, 0), content, "sans", 45, align="m", anchor="mt")
    return imutil.to_segment(im)

  await matcher.finish(await misc.to_thread(make))
