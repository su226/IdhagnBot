from util.config import BaseState, Field
from aiohttp import ClientSession, ClientConnectionError
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.params import CommandArg
from nonebot.log import logger
import nonebot
import os

class State(BaseState):
  __file__ = "emojimix"
  unsupported: set[str] = Field(default_factory=set)

CACHE_DIR = "states/emojimix_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
def write_cache(cache: str, data: bytes):
  try:
    with open(cache, "wb") as f:
      f.write(data)
  except:
    logger.exception(f"写入缓存失败：{cache}")

STATE = State.load()
API = "https://www.gstatic.com/android/keyboard/emojikitchen"
EMOJIS = {
  '☕': '20201001',
  '⛄': '20201001',
  '❤️\u200d🩹': '20210218',
  '⭐': '20201001',
  '🌇': '20210831',
  '🌈': '20201001',
  '🌍': '20201001',
  '🌛': '20201001',
  '🌜': '20201001',
  '🌞': '20201001',
  '🌟': '20201001',
  '🌭': '20201001',
  '🌲': '20201001',
  '🌵': '20201001',
  '🌷': '20201001',
  '🌸': '20210218',
  '🌹': '20201001',
  '🌼': '20201001',
  '🍊': '20211115',
  '🍋': '20210521',
  '🍌': '20211115',
  '🍍': '20201001',
  '🍓': '20210831',
  '🍞': '20210831',
  '🎁': '20211115',
  '🎂': '20201001',
  '🎃': '20201001',
  '🎈': '20201001',
  '🎊': '20201001',
  '🎧': '20210521',
  '🏆': '20211115',
  '🐌': '20210218',
  '🐐': '20210831',
  '🐙': '20201001',
  '🐝': '20201001',
  '🐟': '20210831',
  '🐢': '20201001',
  '🐦': '20210831',
  '🐧': '20211115',
  '🐨': '20201001',
  '🐩': '20211115',
  '🐭': '20201001',
  '🐯': '20220110',
  '🐰': '20201001',
  '🐱': '20201001',
  '🐵': '20201001',
  '🐶': '20211115',
  '🐷': '20201001',
  '🐻': '20210831',
  '🐼': '20201001',
  '👀': '20201001',
  '👑': '20201001',
  '👻': '20201001',
  '👽': '20201001',
  '👿': '20201001',
  '💀': '20201001',
  '💋': '20201001',
  '💌': '20201001',
  '💎': '20201001',
  '💐': '20201001',
  '💓': '20201001',
  '💔': '20201001',
  '💕': '20201001',
  '💖': '20201001',
  '💗': '20201001',
  '💘': '20201001',
  '💙': '20201001',
  '💚': '20201001',
  '💛': '20201001',
  '💜': '20201001',
  '💝': '20201001',
  '💞': '20201001',
  '💟': '20201001',
  '💩': '20201001',
  '💫': '20201001',
  '💯': '20201001',
  '📰': '20201001',
  '🔥': '20201001',
  '🔮': '20201001',
  '🖤': '20201001',
  '😀': '20201001',
  '😁': '20201001',
  '😂': '20201001',
  '😃': '20201001',
  '😄': '20201001',
  '😅': '20201001',
  '😆': '20201001',
  '😇': '20201001',
  '😈': '20201001',
  '😉': '20201001',
  '😊': '20201001',
  '😋': '20201001',
  '😌': '20201001',
  '😍': '20201001',
  '😎': '20201001',
  '😏': '20201001',
  '😐': '20201001',
  '😑': '20201001',
  '😒': '20201001',
  '😓': '20201001',
  '😔': '20201001',
  '😕': '20201001',
  '😖': '20201001',
  '😗': '20201001',
  '😘': '20201001',
  '😙': '20201001',
  '😚': '20201001',
  '😛': '20201001',
  '😜': '20201001',
  '😝': '20201001',
  '😞': '20201001',
  '😟': '20201001',
  '😠': '20201001',
  '😡': '20201001',
  '😢': '20201001',
  '😣': '20201001',
  '😤': '20201001',
  '😥': '20201001',
  '😦': '20201001',
  '😧': '20201001',
  '😨': '20201001',
  '😩': '20201001',
  '😪': '20201001',
  '😫': '20201001',
  '😬': '20201001',
  '😭': '20201001',
  '😮': '20201001',
  '😮\u200d💨': '20210218',
  '😯': '20201001',
  '😰': '20201001',
  '😱': '20201001',
  '😲': '20201001',
  '😳': '20201001',
  '😴': '20201001',
  '😵': '20201001',
  '😶': '20201001',
  '😶\u200d🌫️': '20210218',
  '😷': '20201001',
  '🙁': '20201001',
  '🙂': '20201001',
  '🙃': '20201001',
  '🙄': '20201001',
  '🙈': '20201001',
  '🤍': '20201001',
  '🤎': '20201001',
  '🤐': '20201001',
  '🤑': '20201001',
  '🤒': '20201001',
  '🤓': '20201001',
  '🤔': '20201001',
  '🤕': '20201001',
  '🤖': '20201001',
  '🤗': '20201001',
  '🤠': '20201001',
  '🤡': '20201001',
  '🤢': '20201001',
  '🤣': '20201001',
  '🤤': '20201001',
  '🤥': '20201001',
  '🤧': '20201001',
  '🤨': '20201001',
  '🤩': '20201001',
  '🤪': '20201001',
  '🤫': '20201001',
  '🤬': '20201001',
  '🤭': '20201001',
  '🤮': '20201001',
  '🤯': '20201001',
  '🥑': '20201001',
  '🥰': '20201001',
  '🥱': '20201001',
  '🥲': '20201001',
  '🥳': '20201001',
  '🥴': '20201001',
  '🥵': '20201001',
  '🥶': '20201001',
  '🥸': '20201001',
  '\U0001f979': '20211115',
  '🥺': '20201001',
  '🦁': '20201001',
  '🦂': '20210218',
  '🦄': '20210831',
  '🦇': '20201001',
  '🦉': '20210831',
  '🦌': '20201001',
  '🦔': '20201001',
  '🦙': '20201001',
  '🦝': '20211115',
  '🦠': '20201001',
  '🦥': '20201001',
  '🧀': '20201001',
  '🧁': '20201001',
  '🧐': '20201001',
  '🧡': '20201001',
  '🪄': '20210521',
  '🪵': '20211115',
  '\U0001fae0': '20211115',
  '\U0001fae1': '20211115',
  '\U0001fae2': '20211115',
  '\U0001fae3': '20211115',
  '\U0001fae4': '20211115',
  '\U0001fae5': '20211115'
}
def get_code(emoji: str) -> str:
  return "_".join(map(lambda ch: "u{:x}".format(ord(ch)), emoji))
SUPPORTED_STR = "支持的 emoji（并不是所有组合都存在）：\n" + "\n".join(map(lambda x: f"{x}（{get_code(x)}）", EMOJIS.keys()))

emojimix = nonebot.on_command("emojimix", aliases={"缝合", "emoji", "mix"})
emojimix.__cmd__ = ["emojimix", "缝合", "emoji", "mix"]
emojimix.__brief__ = "缝合两个emoji"
emojimix.__doc__ = '''\
/emojimix - 查看支持的emoji
/emojimix <emoji1>+<emoji2> - 缝合两个emoji
数据来自 https://tikolu.net/emojimix
图片来自 Google'''
@emojimix.handle()
async def handle_emojimix(args = CommandArg()):
  emojis = args.extract_plain_text().split("+")
  if len(emojis) == 0:
    await emojimix.finish(SUPPORTED_STR)
  elif len(emojis) != 2:
    await emojimix.finish("请输入加号分割的两个 emoji")
  emoji1, emoji2 = emojis
  code1 = get_code(emoji1)
  code2 = get_code(emoji2)
  file1 = f"{code1}_{code2}"
  file2 = f"{code2}_{code1}"
  cache1 = os.path.abspath(f"{CACHE_DIR}/{file1}.png")
  cache2 = os.path.abspath(f"{CACHE_DIR}/{file2}.png")
  if os.path.exists(cache1):
    await emojimix.finish(MessageSegment.image("file://" + cache1))
  if os.path.exists(cache2):
    await emojimix.finish(MessageSegment.image("file://" + cache2))
  if file1 in STATE.unsupported:
    await emojimix.finish("组合不存在")
  if file2 in STATE.unsupported:
    await emojimix.finish("组合不存在")
  errors = []
  if emoji1 not in EMOJIS:
    errors.append(f"不支持 {emoji1}（{code1}）")
  if emoji2 not in EMOJIS:
    errors.append(f"不支持 {emoji2}（{code2}）")
  if errors:
    await emojimix.finish("\n".join(errors))
  async with ClientSession() as http:
    try:
      response = await http.get(f"{API}/{EMOJIS[emoji1]}/{code1}/{file1}.png")
      if response.status == 200:
        image = await response.read()
        write_cache(cache1, image)
        await emojimix.finish(MessageSegment.image(image))
      response = await http.get(f"{API}/{EMOJIS[emoji2]}/{code2}/{file2}.png")
      if response.status == 200:
        image = await response.read()
        write_cache(cache2, image)
        await emojimix.finish(MessageSegment.image(image))
      STATE.unsupported.add(file1)
      STATE.dump()
      await emojimix.finish("组合不存在")
    except ClientConnectionError:
      await emojimix.finish("网络错误")
