from argparse import Namespace
from io import BytesIO
import os

from PIL import Image, ImageDraw
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot.params import ShellCommandArgs

from util import resources, text, context, command
from util.helper import notnone
from ..util import get_image_and_user

plugin_dir = os.path.dirname(os.path.abspath(__file__))
GENDERS = {
  "male": "他",
  "female": "她",
  "unknown": "它",
  "animal": "牠",
  "god": "祂",
}

parser = ArgumentParser("/小天使", add_help=False)
parser.add_argument("target", nargs="?", default="", metavar="目标", help="可使用@、QQ号、昵称、群名片或图片链接")
parser.add_argument("-name", "-名字", help="自定义名字，对于图片链接必须指定，对于QQ用户默认使用昵称")
parser.add_argument("-gender", "-性别", help="自定义性别，对于图片链接默认为未知，对于QQ用户默认为资料性别，可以是\"male\"（他）、\"female\"（她）、\"unknown\"（它）、\"animal\"（牠）、\"god\"（祂）")
matcher = (command.CommandBuilder("petpet_v2.trash", "小天使", "angel")
  .category("petpet_v2")
  .shell(parser)
  .build())
@matcher.handle()
async def handler(bot: Bot, event: MessageEvent, args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await matcher.finish(args.message)
  errors, avatar, user = await get_image_and_user(bot, event, args.target, event.self_id)
  if errors:
    await matcher.finish("\n".join(errors))
  if user is not None:
    try:
      info = await bot.get_group_member_info(group_id=context.get_event_context(event), user_id=user)
      name = info["card"] or info["nickname"]
      gender = info["sex"]
    except:
      info = await bot.get_stranger_info(user_id=user)
      name = info["nickname"]
      gender = info["sex"]
  else:
    name = None
    gender = "unknown"
  if args.name is not None:
    name = args.name
  if args.gender is not None:
    gender = args.gender
  if name is None:
    await matcher.finish(f"请使用 -name 指定名字")

  im = Image.new("RGB", (600, 730), (255, 255, 255))
  draw = ImageDraw.Draw(im)

  layout = text.layout(f"请问你们看到{name}了吗?", "sans bold", 70)
  width, height = layout.get_pixel_size()
  if width > 560 * 2.5:
    await matcher.finish("名字过长")
  im2 = text.render(layout)
  if width > 560:
    im2 = im2.resize((560, int(height / width * 560)), Image.ANTIALIAS)
  im.paste(im2, (300 - im2.width // 2, 50 - im2.height // 2), im2)

  avatar = notnone(avatar).resize((500, 500), Image.ANTIALIAS)
  im.paste(avatar, (50, 110), avatar)

  font = resources.font("sans-bold", 48)
  draw.text((300, 610), "非常可爱！简直就是小天使", (0, 0, 0), font, "ma")

  font = resources.font("sans-bold", 26)
  draw.text((300, 680), f"{GENDERS[gender]}没失踪也没怎么样  我只是觉得你们都该看一下", (0, 0, 0), font, "ma")

  f = BytesIO()
  im.save(f, "PNG")
  await matcher.finish(MessageSegment.image(f))
