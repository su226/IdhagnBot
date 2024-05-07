import json
import os
import random
import re
from typing import Dict, List, Tuple, cast

import aiohttp
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from pygtrie import CharTrie

from util import command, context, misc


class Data:
  revisions: List[int]
  points: List[str]
  trie: CharTrie
  mixables: List[List[int]]
  pairs: Dict[Tuple[int, int], int]
  pairs_key: List[Tuple[int, int]]

  def __init__(self) -> None:
    with open(DATA_PATH) as f:
      raw = json.load(f)
    self.revisions = raw["revisions"]
    self.points = raw["points"]
    self.trie = CharTrie((v, k) for k, v in enumerate(self.points))
    self.mixables = raw["mixables"]
    self.pairs = {
      cast(Tuple[int, int], tuple(int(x) for x in k.split(","))): v
      for k, v in raw["pairs"].items()
    }
    self.pairs_key = list(self.pairs)

  @staticmethod
  def get_code(emoji: str) -> str:
    return "-".join(f"u{ord(ch):x}" for ch in emoji)

  async def get_image(self, first_id: int, second_id: int) -> bytes:
    revision = self.revisions[self.pairs[first_id, second_id]]
    first_code = self.get_code(self.points[first_id])
    second_code = self.get_code(self.points[second_id])
    filename = f"{first_code}_{second_code}.png"
    if os.path.exists(cache := os.path.join(CACHE_DIR, filename)):
      with open(cache, "rb") as f:
        return f.read()
    http = misc.http()
    async with http.get(f"{API}/{revision}/{first_code}/{filename}") as response:
      data = await response.read()
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache, "wb") as f:
      f.write(data)
    return data


DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")
CACHE_DIR = os.path.join("states", "emojimix_cache")
API = "https://www.gstatic.com/android/keyboard/emojikitchen"
IGNORE_RE = re.compile(r"^[\s\u200b\ufe0f\U0001f3fb-\U0001f3ff\U0001F9B0-\U0001F9B3]+")
DATA = Data()


emojimix = (
  command.CommandBuilder("emojimix", "emojimix", "缝合", "emoji", "mix")
  .brief("缝合两个emoji")
  .usage('''\
/emojimix - 随机缝合
/emojimix list - 查看支持的emoji
/emojimix <emoji> list - 查看可以和这个emoji缝合的其他emoji
/emojimix <emoji> - 半随机缝合
/emojimix <emoji1>+<emoji2> - 缝合两个emoji
数据来自 https://github.com/alcor/emoji-supply
图片来自 Google''')
  .build()
)
@emojimix.handle()
async def handle_emojimix(bot: Bot, event: Event, args: Message = CommandArg()):
  argv = args.extract_plain_text().rstrip()

  if not argv:
    first_id, second_id = random.choice(DATA.pairs_key)
    try:
      image = await DATA.get_image(first_id, second_id)
    except aiohttp.ClientError:
      await emojimix.finish("网络错误")
    first = DATA.points[first_id]
    second = DATA.points[second_id]
    await emojimix.finish(f"{first}+{second}=" + MessageSegment.image(image))

  if argv == "list":
    self_name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = [misc.forward_node(event.self_id, self_name, "支持的 emoji（并不是所有组合都存在）：")]
    for emoji in misc.chunked(DATA.points, 50):
      content = " | ".join(emoji)
      nodes.append(misc.forward_node(event.self_id, self_name, content))
    await misc.send_forward_msg(bot, event, *nodes)
    await emojimix.finish()

  first_step = DATA.trie.longest_prefix(argv)
  if not first_step:
    await command.finish_with_usage()

  first_id = cast(int, first_step.value)
  argv = IGNORE_RE.sub("", argv[len(first_step.key):])

  if not argv:
    second_id = random.choice(DATA.mixables[first_id])
    try:
      image = await DATA.get_image(first_id, second_id)
    except aiohttp.ClientError:
      await emojimix.finish("网络错误")
    first = DATA.points[first_id]
    second = DATA.points[second_id]
    await emojimix.finish(f"{first}+{second}=" + MessageSegment.image(image))

  if argv == "list":
    self_name = await context.get_card_or_name(bot, event, event.self_id)
    emoji = DATA.points[first_step.value]
    nodes = [misc.forward_node(event.self_id, self_name, f"可以和 {emoji} 组合的 emoji：")]
    for emoji_ids in misc.chunked(DATA.mixables[first_step.value], 50):
      content = " | ".join(DATA.points[id] for id in emoji_ids)
      nodes.append(misc.forward_node(event.self_id, self_name, content))
    await misc.send_forward_msg(bot, event, *nodes)
    await emojimix.finish()

  argv = misc.removeprefix(argv, "+").lstrip()
  second_step = DATA.trie.longest_prefix(argv)
  if not second_step:
    await command.finish_with_usage()
  argv = IGNORE_RE.sub("", argv[len(first_step.key):])
  if argv:
    await command.finish_with_usage()

  second_id = cast(int, second_step.value)
  first = DATA.points[first_id]
  second = DATA.points[second_id]
  try:
    try:
      image = await DATA.get_image(first_id, second_id)
    except KeyError:
      image = await DATA.get_image(second_id, first_id)
  except aiohttp.ClientError:
    await emojimix.finish("网络错误")
  except KeyError:
    await emojimix.finish(f"似乎不能组合 {first} 和 {second}")
  await emojimix.finish(f"{first}+{second}=" + MessageSegment.image(image))
