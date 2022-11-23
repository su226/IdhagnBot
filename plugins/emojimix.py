import os
import random
import re
from typing import List, Optional, Tuple

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg

from util import command, context, misc

CACHE_DIR = "states/emojimix_cache"
API = "https://www.gstatic.com/android/keyboard/emojikitchen"
EMOJIS: List[Tuple[str, str]] = [
  ('☁️', '20201001'),
  ('☕', '20201001'),
  ('☹️', '20201001'),
  ('☺️', '20201001'),
  ('♥️', '20201001'),
  ('⚽', '20220406'),
  ('⛄', '20201001'),
  ('❣️', '20201001'),
  ('❤️', '20201001'),
  ('❤️\u200d🩹', '20210218'),
  ('⭐', '20201001'),
  ('🌇', '20210831'),
  ('🌈', '20201001'),
  ('🌍', '20201001'),
  ('🌛', '20201001'),
  ('🌜', '20201001'),
  ('🌞', '20201001'),
  ('🌟', '20201001'),
  ('🌪️', '20201001'),
  ('🌭', '20201001'),
  ('🌲', '20201001'),
  ('🌵', '20201001'),
  ('🌶️', '20201001'),
  ('🌷', '20201001'),
  ('🌸', '20210218'),
  ('🌹', '20201001'),
  ('🌼', '20201001'),
  ('🍄', '20220406'),
  ('🍉', '20220406'),
  ('🍊', '20211115'),
  ('🍋', '20210521'),
  ('🍌', '20211115'),
  ('🍍', '20201001'),
  ('🍒', '20220406'),
  ('🍓', '20210831'),
  ('🍞', '20210831'),
  ('🍽️', '20201001'),
  ('🎁', '20211115'),
  ('🎂', '20201001'),
  ('🎃', '20201001'),
  ('🎈', '20201001'),
  ('🎊', '20201001'),
  ('🎗️', '20201001'),
  ('🎧', '20210521'),
  ('🏅', '20220203'),
  ('🏆', '20211115'),
  ('🐌', '20210218'),
  ('🐐', '20210831'),
  ('🐙', '20201001'),
  ('🐝', '20201001'),
  ('🐟', '20210831'),
  ('🐢', '20201001'),
  ('🐦', '20210831'),
  ('🐧', '20211115'),
  ('🐨', '20201001'),
  ('🐩', '20211115'),
  ('🐭', '20201001'),
  ('🐯', '20220110'),
  ('🐰', '20201001'),
  ('🐱', '20201001'),
  ('🐵', '20201001'),
  ('🐶', '20211115'),
  ('🐷', '20201001'),
  ('🐻', '20210831'),
  ('🐼', '20201001'),
  ('👀', '20201001'),
  ('👁️', '20201001'),
  ('👑', '20201001'),
  ('👻', '20201001'),
  ('👽', '20201001'),
  ('👿', '20201001'),
  ('💀', '20201001'),
  ('💋', '20201001'),
  ('💌', '20201001'),
  ('💎', '20201001'),
  ('💐', '20201001'),
  ('💓', '20201001'),
  ('💔', '20201001'),
  ('💕', '20201001'),
  ('💖', '20201001'),
  ('💗', '20201001'),
  ('💘', '20201001'),
  ('💙', '20201001'),
  ('💚', '20201001'),
  ('💛', '20201001'),
  ('💜', '20201001'),
  ('💝', '20201001'),
  ('💞', '20201001'),
  ('💟', '20201001'),
  ('💥', '20220203'),
  ('💩', '20201001'),
  ('💫', '20201001'),
  ('💬', '20220203'),
  ('💯', '20201001'),
  ('📰', '20201001'),
  ('🔥', '20201001'),
  ('🔮', '20201001'),
  ('🕳️', '20201001'),
  ('🕷️', '20201001'),
  ('🖤', '20201001'),
  ('😀', '20201001'),
  ('😁', '20201001'),
  ('😂', '20201001'),
  ('😃', '20201001'),
  ('😄', '20201001'),
  ('😅', '20201001'),
  ('😆', '20201001'),
  ('😇', '20201001'),
  ('😈', '20201001'),
  ('😉', '20201001'),
  ('😊', '20201001'),
  ('😋', '20201001'),
  ('😌', '20201001'),
  ('😍', '20201001'),
  ('😎', '20201001'),
  ('😏', '20201001'),
  ('😐', '20201001'),
  ('😑', '20201001'),
  ('😒', '20201001'),
  ('😓', '20201001'),
  ('😔', '20201001'),
  ('😕', '20201001'),
  ('😖', '20201001'),
  ('😗', '20201001'),
  ('😘', '20201001'),
  ('😙', '20201001'),
  ('😚', '20201001'),
  ('😛', '20201001'),
  ('😜', '20201001'),
  ('😝', '20201001'),
  ('😞', '20201001'),
  ('😟', '20201001'),
  ('😠', '20201001'),
  ('😡', '20201001'),
  ('😢', '20201001'),
  ('😣', '20201001'),
  ('😤', '20201001'),
  ('😥', '20201001'),
  ('😦', '20201001'),
  ('😧', '20201001'),
  ('😨', '20201001'),
  ('😩', '20201001'),
  ('😪', '20201001'),
  ('😫', '20201001'),
  ('😬', '20201001'),
  ('😭', '20201001'),
  ('😮', '20201001'),
  ('😮\u200d💨', '20210218'),
  ('😯', '20201001'),
  ('😰', '20201001'),
  ('😱', '20201001'),
  ('😲', '20201001'),
  ('😳', '20201001'),
  ('😴', '20201001'),
  ('😵', '20201001'),
  ('😶', '20201001'),
  ('😶\u200d🌫️', '20210218'),
  ('😷', '20201001'),
  ('🙁', '20201001'),
  ('🙂', '20201001'),
  ('🙃', '20201001'),
  ('🙄', '20201001'),
  ('🙈', '20201001'),
  ('🤍', '20201001'),
  ('🤎', '20201001'),
  ('🤐', '20201001'),
  ('🤑', '20201001'),
  ('🤒', '20201001'),
  ('🤓', '20201001'),
  ('🤔', '20201001'),
  ('🤕', '20201001'),
  ('🤖', '20201001'),
  ('🤗', '20201001'),
  ('🤠', '20201001'),
  ('🤡', '20201001'),
  ('🤢', '20201001'),
  ('🤣', '20201001'),
  ('🤤', '20201001'),
  ('🤥', '20201001'),
  ('🤧', '20201001'),
  ('🤨', '20201001'),
  ('🤩', '20201001'),
  ('🤪', '20201001'),
  ('🤫', '20201001'),
  ('🤬', '20201001'),
  ('🤭', '20201001'),
  ('🤮', '20201001'),
  ('🤯', '20201001'),
  ('🥇', '20220203'),
  ('🥈', '20220203'),
  ('🥉', '20220203'),
  ('🥑', '20201001'),
  ('🥰', '20201001'),
  ('🥱', '20201001'),
  ('🥲', '20201001'),
  ('🥳', '20201001'),
  ('🥴', '20201001'),
  ('🥵', '20201001'),
  ('🥶', '20201001'),
  ('🥸', '20201001'),
  ('\U0001f979', '20211115'),
  ('🥺', '20201001'),
  ('🦁', '20201001'),
  ('🦂', '20210218'),
  ('🦄', '20210831'),
  ('🦇', '20201001'),
  ('🦉', '20210831'),
  ('🦌', '20201001'),
  ('🦔', '20201001'),
  ('🦙', '20201001'),
  ('🦝', '20211115'),
  ('🦠', '20201001'),
  ('🦥', '20201001'),
  ('🦴', '20220203'),
  ('🦷', '20220203'),
  ('🧀', '20201001'),
  ('🧁', '20201001'),
  ('🧐', '20201001'),
  ('🧠', '20220203'),
  ('🧡', '20201001'),
  ('🪄', '20210521'),
  ('🪨', '20220406'),
  ('🪵', '20211115'),
  ('🫀', '20220203'),
  ('🫁', '20220203'),
  ('\U0001fae0', '20211115'),
  ('\U0001fae1', '20211115'),
  ('\U0001fae2', '20211115'),
  ('\U0001fae3', '20211115'),
  ('\U0001fae4', '20211115'),
  ('\U0001fae5', '20211115'),
  ('\U0001fae6', '20220203'),
]
IGNORE_RE = re.compile(r"[+\s\u200b\ufe0f\U0001f3fb-\U0001f3ff\U0001F9B0-\U0001F9B3]")


def get_code(emoji: str) -> str:
  return "-".join(map(lambda ch: "u{:x}".format(ord(ch)), emoji))


def split_emojis(argv: str) -> Tuple[Tuple[str, str], Optional[Tuple[str, str]]]:
  argv = IGNORE_RE.sub("", argv)
  first_match: Optional[Tuple[str, str]] = None
  for char, date in EMOJIS:
    stripped = IGNORE_RE.sub("", char)
    if argv.startswith(stripped):
      argv = misc.removeprefix(argv, stripped)
      first_match = char, date
      break
  else:
    raise KeyError("No match")
  if not argv:
    return first_match, None
  for char, date in EMOJIS:
    if argv == IGNORE_RE.sub("", char):
      return first_match, (char, date)
  else:
    raise KeyError("No match")


async def get_image(emoji1: str, date1: str, emoji2: str, date2: str) -> Optional[bytes]:
  code1 = get_code(emoji1)
  code2 = get_code(emoji2)
  file1 = f"{code1}_{code2}"
  file2 = f"{code2}_{code1}"
  cache1 = f"{CACHE_DIR}/{file1}"
  cache2 = f"{CACHE_DIR}/{file2}"
  if os.path.exists(f"{cache1}.unsupported") or os.path.exists(f"{cache2}.unsupported"):
    return None
  cache1 += ".png"
  if os.path.exists(cache1):
    with open(cache1, "rb") as f:
      return f.read()
  cache2 += ".png"
  if os.path.exists(cache2):
    with open(cache2, "rb") as f:
      return f.read()
  http = misc.http()
  async with http.get(f"{API}/{date1}/{code1}/{file1}.png") as response:
    if response.status == 200:
      image = await response.read()
      with open(f"{CACHE_DIR}/{file1}.png", "wb") as f:
        f.write(image)
      return image
  async with http.get(f"{API}/{date2}/{code2}/{file2}.png") as response:
    if response.status == 200:
      image = await response.read()
      with open(f"{CACHE_DIR}/{file1}.png", "wb") as f:
        f.write(image)
      return image
  with open(f"{CACHE_DIR}/{file1}.unsupported", "w"):
    pass


emojimix = (
  command.CommandBuilder("emojimix", "emojimix", "缝合", "emoji", "mix")
  .brief("缝合两个emoji")
  .usage('''\
/emojimix - 查看支持的emoji
/emojimix random - 随机缝合
/emojimix <emoji> - 半随机缝合
/emojimix <emoji1>+<emoji2> - 缝合两个emoji
数据来自 https://tikolu.net/emojimix
图片来自 Google''')
  .build()
)
@emojimix.handle()
async def handle_emojimix(bot: Bot, event: Event, args: Message = CommandArg()):
  argv = args.extract_plain_text().rstrip()
  if not argv:
    self_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = [misc.forward_node(event.self_id, self_name, "支持的 emoji（并不是所有组合都存在）：")]
    for i in misc.chunked(EMOJIS, 50):
      content = " | ".join(x[0] for x in i)
      nodes.append(misc.forward_node(event.self_id, self_name, content))
    await misc.send_forward_msg(bot, event, *nodes)
    await emojimix.finish()

  if argv == "random":
    emoji1 = emoji2 = ""
    result = None
    while result is None:
      emoji1, date1 = random.choice(EMOJIS)
      emoji2, date2 = random.choice(EMOJIS)
      result = await get_image(emoji1, date1, emoji2, date2)
    await emojimix.finish(f"{emoji1}+{emoji2}=" + MessageSegment.image(result))

  try:
    (emoji1, date1), pair2 = split_emojis(argv)
  except KeyError:
    await emojimix.finish(emojimix.__doc__)
  if pair2 is None:
    emoji2 = ""
    result = None
    while result is None:
      emoji2, date2 = random.choice(EMOJIS)
      result = await get_image(emoji1, date1, emoji2, date2)
    await emojimix.finish(f"{emoji1}+{emoji2}=" + MessageSegment.image(result))

  try:
    result = await get_image(emoji1, date1, pair2[0], pair2[1])
    if result is None:
      await emojimix.finish("似乎不能这么组合")
    await emojimix.finish(MessageSegment.image(result))
  except aiohttp.ClientError:
    await emojimix.finish("网络错误")
