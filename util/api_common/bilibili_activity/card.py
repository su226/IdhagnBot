import asyncio
from io import BytesIO
from typing import Dict, Optional

from PIL import Image

from util import imutil, misc, textutil
from util.images.card import CONTENT_WIDTH, PADDING, WIDTH, Render

from . import RichText, RichTextEmotion, RichTextLink, Topic

EMOTION_SIZE = 48


async def fetch_emotion(url: str) -> Image.Image:
  async with misc.http().get(url) as response:
    data = await response.read()
  return await misc.to_thread(lambda:
    Image.open(BytesIO(data)).resize((EMOTION_SIZE, EMOTION_SIZE), imutil.scale_resample())
  )


async def fetch_emotions(richtext: RichText) -> Dict[str, Image.Image]:
  urls = [node.url for node in richtext if isinstance(node, RichTextEmotion)]
  surfaces = await asyncio.gather(*[fetch_emotion(url) for url in urls])
  return {url: surface for url, surface in zip(urls, surfaces)}


class CardTopic(Render):
  def __init__(self, topic: Optional[Topic]) -> None:
    self._im = None
    if topic:
      self._im = textutil.render("#" + topic.name, "sans", 32, color=0x008ac5, box=CONTENT_WIDTH)

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self._im.height if self._im else 0

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    if self._im:
      dst.paste(self._im, (x + PADDING, y), self._im)


class CardRichText(Render):
  def __init__(
    self, richtext: RichText, emotions: Dict[str, Image.Image], size: int, lines: int,
    topic: Optional[Topic] = None
  ) -> None:
    render = textutil.RichText().set_font("sans", size)
    render.set_width(CONTENT_WIDTH).set_height(-lines).set_ellipsize("end")
    if topic:
      render.append_markup(f"<span color='#008ac5'>#{textutil.escape(topic.name)}</span>\n")
    for node in richtext:
      if isinstance(node, RichTextEmotion):
        render.append_image(emotions[node.url])
      elif isinstance(node, RichTextLink):
        render.append_markup(f"<span color='#008ac5'>{textutil.escape(node.text)}</span>")
      else:
        render.append(node)
    self._im = render.render()

  def get_width(self) -> int:
    return WIDTH

  def get_height(self) -> int:
    return self._im.height

  def render(self, dst: Image.Image, x: int, y: int) -> None:
    dst.paste(self._im, (x + PADDING, y), self._im)
