import re
from argparse import Namespace

import aiohttp
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.exception import ParserExit
from nonebot.params import CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser

from util import command

ENGLISH_RE = re.compile(r"^[A-Za-z0-9]+$")

NBNHHSH_API = "https://lab.magiconch.com/api/nbnhhsh/guess"
COUPLET_API = "https://ai-backend.binwang.me/v0.2/couplet/"
ALIPAY_VOICE_API = "https://mm.cqu.cc/share/zhifubaodaozhang/{}.mp3"

NBNHHSH_USAGE = (
  "/能不能好好说话 <...缩写>\n只能输入字母和数字\n接口来自https://lab.magiconch.com/nbnhhsh/")
nbnhhsh = (
  command.CommandBuilder("fun_api.nbnhhsh", "能不能好好说话", "好好说话", "nbnhhsh")
  .brief("nbnhhsh?")
  .usage(NBNHHSH_USAGE)
  .build())


@nbnhhsh.handle()
async def handle_nbnhhsh(arg: Message = CommandArg()):
  texts = arg.extract_plain_text().split()
  if not texts or not all(ENGLISH_RE.match(text) for text in texts):
    await nbnhhsh.finish(NBNHHSH_USAGE)
  async with aiohttp.ClientSession() as http:
    async with http.post(NBNHHSH_API, data={"text": ",".join(texts)}) as response:
      datas = await response.json()
  segments = []
  for text, data in zip(texts, datas):
    if "trans" in data:
      segments.append(f"{text}可以指：" + "、".join(data["trans"]))
    elif data["inputting"]:
      segments.append(f"{text}可能是：" + "、".join(data["inputting"]))
    else:
      segments.append(f"神奇海螺也不知道{text}诶~")
  await nbnhhsh.finish("\n\n".join(segments))

couplet_parser = ArgumentParser(add_help=False, epilog="接口来自https://ai.binwang.me/couplet/")
couplet_parser.add_argument("text", metavar="上联内容")
couplet_parser.add_argument(
  "-score", "-得分", metavar="分值", type=float, default=float("-inf"),
  help="下联的最小得分（默认：-∞）")
couplet = (
  command.CommandBuilder("fun_api.couplet", "对联")
  .brief("王斌给您对对联 -_-!")
  .shell(couplet_parser)
  .build())


@couplet.handle()
async def handle_couplet(args: Namespace | ParserExit = ShellCommandArgs()):
  if isinstance(args, ParserExit):
    await couplet.finish(args.message)
  async with aiohttp.ClientSession() as http:
    async with http.get(COUPLET_API + args.text) as response:
      data = await response.json()
  result = [
    (result, score) for result, score in zip(data["output"], data["score"]) if score > args.score]
  if not result:
    await couplet.finish(f"没有结果（最高得分：{data['score'][0]:.2f}）")
  segments = [f"“{result}” 得分：{score:.2f}" for result, score in result]
  await couplet.finish("\n".join(segments))

ALIPAY_VOICE_USAGE = (
  "/支付宝到帐 <金额>\n范围从0.01到999999999999.99，且只能有两位小数\n"
  "接口来自https://mm.cqu.cc/share/zhifubaodaozhang/")
alipay_voice = (
  command.CommandBuilder("fun_api.alipay_voice", "支付宝到帐", "支付宝", "zfb")
  .brief("支付宝到帐一亿元")
  .usage(ALIPAY_VOICE_USAGE)
  .build())


@alipay_voice.handle()
async def handle_alipay_voice(arg: Message = CommandArg()):
  try:
    value = float(arg.extract_plain_text().rstrip())
    if value * 100 % 1 > 0:
      raise ValueError("只能有两位小数")
    elif value < 0.01 or value > 999999999999.99:
      raise ValueError("超出范围")
  except ValueError:
    await alipay_voice.finish(ALIPAY_VOICE_USAGE)
  value_str = str(int(value)) if value % 1 == 0 else str(value)
  await alipay_voice.finish(MessageSegment.record(
    f"https://mm.cqu.cc/share/zhifubaodaozhang/mp3/{value_str}.mp3"))

today = (
  command.CommandBuilder("fun_api.today", "今天", "today")
  .brief("查看历史上的今天")
  .usage("接口来自https://www.ipip5.com/today/")
  .build())


@today.handle()
async def handle_today():
  async with aiohttp.ClientSession() as http:
    response = await http.get("https://www.ipip5.com/today/api.php?type=json")
    data = await response.json()
  result = [f"今天是{data['result'][-1]['year']}年{data['today']}，历史上的今天是："]
  for i in data["result"][:-1]:
    result.append(f"{i['year']}: {i['title']}")
  await today.finish("\n".join(result))
