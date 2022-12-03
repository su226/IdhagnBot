import re
from argparse import Namespace

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser

from util import command, misc

ENGLISH_RE = re.compile(r"^[A-Za-z0-9]+$")
SPACE_RE = re.compile(r"\s+")
NBNHHSH_API = "https://lab.magiconch.com/api/nbnhhsh/guess"
COUPLET_API = "https://ai-backend.binwang.me/v0.2/couplet/"
ALIPAY_VOICE_API = "https://mm.cqu.cc/share/zhifubaodaozhang/{}.mp3"
DINGZHEN_API = "https://api.aya1.top/randomdj?r=0"
HITOKOTO_API = "https://v1.hitokoto.cn/?"
HITOKOTO_LIKE_API = "https://hitokoto.cn/api/common/v1/like?sentence_uuid="
HITOKOTO_TYPES = {
  "a": "动画", "b": "漫画", "c": "游戏", "d": "文学", "e": "原创", "f": "来自网络", "g": "其他",
  "h": "影视", "i": "诗词", "j": "网易云", "k": "哲学", "l": "抖机灵"
}


nbnhhsh = (
  command.CommandBuilder("fun_api.nbnhhsh", "能不能好好说话", "好好说话", "nbnhhsh")
  .brief("nbnhhsh?")
  .usage('''\
/能不能好好说话 <...缩写>
只能输入字母和数字
接口来自https://lab.magiconch.com/nbnhhsh/''')
  .build()
)
@nbnhhsh.handle()
async def handle_nbnhhsh(arg: Message = CommandArg()) -> None:
  texts = arg.extract_plain_text().split()
  if not texts or not all(ENGLISH_RE.match(text) for text in texts):
    await nbnhhsh.finish(nbnhhsh.__doc__)
  http = misc.http()
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
  "--score", "-s", metavar="分值", type=float, default=float("-inf"),
  help="下联的最小得分（默认：-∞）"
)
couplet = (
  command.CommandBuilder("fun_api.couplet", "对联")
  .brief("王斌给您对对联 -_-!")
  .shell(couplet_parser)
  .build()
)
@couplet.handle()
async def handle_couplet(args: Namespace = ShellCommandArgs()) -> None:
  http = misc.http()
  async with http.get(COUPLET_API + args.text) as response:
    data = await response.json()
  result = [
    (result, score) for result, score in zip(data["output"], data["score"]) if score > args.score]
  if not result:
    await couplet.finish(f"没有结果（最高得分：{data['score'][0]:.2f}）")
  segments = [f"“{result}” 得分：{score:.2f}" for result, score in result]
  await couplet.finish("\n".join(segments))


alipay_voice = (
  command.CommandBuilder("fun_api.alipay_voice", "支付宝到帐", "支付宝", "zfb")
  .brief("支付宝到帐一亿元")
  .usage('''\
/支付宝到帐 <金额>
范围从0.01到999999999999.99，且只能有两位小数
接口来自https://mm.cqu.cc/share/zhifubaodaozhang/''')
  .build()
)
@alipay_voice.handle()
async def handle_alipay_voice(arg: Message = CommandArg()) -> None:
  try:
    value = float(arg.extract_plain_text().rstrip())
    if value < 0.01 or value > 999999999999.99:
      raise ValueError("超出范围")
  except ValueError:
    await alipay_voice.finish(alipay_voice.__doc__)
  value = round(value, 2)
  value_str = str(int(value)) if value % 1 == 0 else str(value)
  await alipay_voice.finish(MessageSegment.record(ALIPAY_VOICE_API.format(value_str)))


dingzhen = (
  command.CommandBuilder("fun_api.dingzhen", "一眼丁真", "丁真")
  .brief("鉴定为假")
  .usage("接口来自https://api.aya1.top/randomdj")
  .build()
)
@dingzhen.handle()
async def handle_dingzhen() -> None:
  http = misc.http()
  async with http.get(DINGZHEN_API) as response:
    data = await response.json()
  await dingzhen.finish(MessageSegment.image(data["url"]))


hitokoto = (
  command.CommandBuilder("fun_api.hitokoto", "一言", "hitokoto")
  .brief("ヒトコト")
  .usage(f'''\
/一言 - 随机类型一言
/一言 <类型> - 指定类型一言
类型是 a-l 之间的字母：{"、".join(x + y for x, y in HITOKOTO_TYPES.items())}
接口来自https://hitokoto.cn''')
  .build()
)
@hitokoto.handle()
async def handle_hitokoto(arg: Message = CommandArg()) -> None:
  types = SPACE_RE.sub("", arg.extract_plain_text()).lower()
  for i in types:
    if i not in HITOKOTO_TYPES:
      await hitokoto.finish(f"{i} 不是有效的类型，类型是 a-l 之间的字母")
  url = HITOKOTO_API + "&".join(f"c={x}" for x in types)
  http = misc.http()
  async with http.get(url) as response:
    data = await response.json()
  async with http.get(HITOKOTO_LIKE_API + data["uuid"]) as response:
    like_data = await response.json()
    likes = like_data["data"][0]["total"]
  from_who = data["from_who"] or ""
  await hitokoto.finish(f'''\
{data["hitokoto"]}
——{from_who}「{data["from"]}」
类型：{HITOKOTO_TYPES[data["type"]]} 点赞：{likes}
https://hitokoto.cn?id={data["id"]}''')
