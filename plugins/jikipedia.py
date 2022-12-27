import base64
import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.padding import PKCS7
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg

from util import command, context, misc

API = "https://api.jikipedia.com/go/search_definitions"
XID_KEY = hashlib.sha256(b"web_2.7.7l_12uh00]35#@(poj[").digest()
XID_PREFIX = b"jikipedia_xid_"


def random_xid() -> str:
  content = XID_PREFIX + str(uuid.uuid4()).encode()
  iv = secrets.token_bytes(16)
  pad = PKCS7(128).padder()
  enc = Cipher(AES(XID_KEY), CBC(iv)).encryptor()
  cip = enc.update(pad.update(content) + pad.finalize()) + enc.finalize()
  return base64.b64encode(iv + cip).decode()


def format_message(definition: Any) -> Message:
  date = datetime.fromisoformat(definition["created_at"]).date().isoformat()
  views = definition["view_count"]
  if views > 1000:
    views_str = f"{views / 1000:.1f}k"
  else:
    views_str = str(views)
  term = definition["term"]["title"]
  id = definition["id"]
  header = f"https://jikipedia.com/definition/{id}\n=== {term} ===\n{date} | {views_str}\n"
  msg = Message(MessageSegment.text(header + definition["plaintext"]))
  for image in definition["images"]:
    msg.append(MessageSegment.image(image["scaled"]["path"]))
  tags = []
  for tag in definition["tags"]:
    tags.append("#" + tag["name"])
  references = []
  for reference in definition["references"]:
    references.append(f"[{reference['title']}] {reference['path']}")
  msg.append(MessageSegment.text("\n" + "\n".join(references) + "\n" + " ".join(tags)))
  return msg


jikipedia = (
  command.CommandBuilder("jikipedia", "小鸡词典", "jikipedia", "查梗")
  .brief("小鸡词典查梗")
  .usage('''
/小鸡词典 <内容>
数据来自小只因……bushi，小鸡词典 jikipedia.com
为了防止被封，有一定冷却时间''')
  .throttle(1, 30)
  .build()
)
@jikipedia.handle()
async def handle_jikipedia(bot: Bot, event: Event, arg: Message = CommandArg()):
  text = arg.extract_plain_text().rstrip()
  lower_text = text.lower()
  if not text:
    await jikipedia.finish(jikipedia.__doc__)
  data = {"phrase": text}
  headers = {
    "XID": random_xid(),
    "Client": "web",
    "Client-Version": "2.7.7l",
  }
  http = misc.http()
  async with http.post(API, json=data, headers=headers) as response:
    data = await response.json()
  if "data" not in data:
    msg = data["message"]["content"]
    await jikipedia.finish(f"错误：{msg}\n可能是访问过于频繁被限流")
  exact = []
  inexact = []
  inexact_set = set()
  for definition in data["data"]:
    term = definition["term"]["title"]
    if term.lower() == lower_text:
      exact.append(format_message(definition))
    elif len(inexact) < 11 and term not in inexact_set:
      inexact.append(term)
      inexact_set.add(term)
  if exact:
    name = await context.get_card_or_name(bot, event, event.self_id)
    nodes = (
      [misc.forward_node(event.self_id, name, "以下结果来自小鸡词典 jikipedia.com")]
      + [misc.forward_node(event.self_id, name, message) for message in exact]
    )
    await misc.send_forward_msg(bot, event, *nodes)
    await jikipedia.finish()
  if inexact:
    if len(inexact) > 10:
      suggestions = "、".join(inexact[:10]) + "……"
    else:
      suggestions = "、".join(inexact)
    await jikipedia.finish(f"没有找到 {text}，你可能要找的是：\n{suggestions}")
  await jikipedia.finish(f"没有找到 {text}")
