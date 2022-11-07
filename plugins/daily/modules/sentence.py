import os

from nonebot.adapters.onebot.v11 import Message

from util import util

from . import DailyCache, Module

SENTENCE_API = "http://open.iciba.com/dsapi/"


class SentenceCache(DailyCache):
  def __init__(self) -> None:
    super().__init__("sentence.jpg")
    self.audio_path = os.path.splitext(self.path)[0] + ".mp3"

  async def update(self) -> None:
    http = util.http()
    async with http.get(SENTENCE_API) as response:
      data = await response.json(content_type=None)
    with open(self.path, "wb") as f:
      async with http.get(data["fenxiang_img"]) as response:
        f.write(await response.read())
    with open(self.audio_path, "wb") as f:
      async with http.get(data["tts"]) as response:
        f.write(await response.read())
    self.write_date()


sentence_cache = SentenceCache()


class SentenceModule(Module):
  async def format(self) -> list[Message]:
    await sentence_cache.ensure()
    return [util.local_image(sentence_cache.path) + "\n你可以发送 /一句 再次查看"]
