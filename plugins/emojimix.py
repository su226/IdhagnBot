import os
import re

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from pydantic import Field

from util import command, context, util
from util.config import BaseState


class State(BaseState):
  __file__ = "emojimix"
  unsupported: set[str] = Field(default_factory=set)


CACHE_DIR = "states/emojimix_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def write_cache(cache: str, data: bytes):
  with open(cache, "wb") as f:
    f.write(data)


STATE = State.load()
API = "https://www.gstatic.com/android/keyboard/emojikitchen"
EMOJIS: list[tuple[str, str]] = [
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
  return "_".join(map(lambda ch: "u{:x}".format(ord(ch)), emoji))


def split_emojis(argv: str) -> tuple[tuple[str, str], tuple[str, str]]:
  argv = IGNORE_RE.sub("", argv)
  first_match: None | tuple[str, str] = None
  for char, date in EMOJIS:
    if argv.startswith(IGNORE_RE.sub("", char)):
      first_match = char, date
      break
  else:
    raise KeyError("No match")
  argv = argv.removeprefix(first_match[0])
  for char, date in EMOJIS:
    if argv == IGNORE_RE.sub("", char):
      return first_match, (char, date)
  else:
    raise KeyError("No match")


emojimix = (
  command.CommandBuilder("emojimix", "emojimix", "缝合", "emoji", "mix")
  .brief("缝合两个emoji")
  .usage('''\
/emojimix - 查看支持的emoji
/emojimix <emoji1>+<emoji2> - 缝合两个emoji
数据来自 https://tikolu.net/emojimix
图片来自 Google''')
  .build())


@emojimix.handle()
async def handle_emojimix(bot: Bot, event: Event, args: Message = CommandArg()):
  argv = args.extract_plain_text().rstrip()
  if not argv:
    self_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = [util.forward_node(event.self_id, self_name, "支持的 emoji（并不是所有组合都存在）：")]
    for i in util.groupbyn(EMOJIS, 50):
      content = " | ".join(x[0] for x in i)
      nodes.append(util.forward_node(event.self_id, self_name, content))
    await util.send_forward_msg(bot, event, *nodes)
    await emojimix.finish()
  try:
    (emoji1, date1), (emoji2, date2) = split_emojis(argv)
  except KeyError:
    await emojimix.finish("似乎不能这么组合")
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
  if file1 in STATE.unsupported or file2 in STATE.unsupported:
    await emojimix.finish("似乎不能这么组合")
  async with aiohttp.ClientSession() as http:
    try:
      response = await http.get(f"{API}/{date1}/{code1}/{file1}.png")
      if response.status == 200:
        image = await response.read()
        write_cache(cache1, image)
        await emojimix.finish(MessageSegment.image(image))
      response = await http.get(f"{API}/{date2}/{code2}/{file2}.png")
      if response.status == 200:
        image = await response.read()
        write_cache(cache2, image)
        await emojimix.finish(MessageSegment.image(image))
      STATE.unsupported.add(file1)
      STATE.dump()
      await emojimix.finish("似乎不能这么组合")
    except aiohttp.ClientError:
      await emojimix.finish("网络错误")
