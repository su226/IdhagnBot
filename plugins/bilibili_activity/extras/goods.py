from typing import Callable

from PIL import Image

from util import imutil, textutil
from util.api_common.bilibili_activity import ExtraGoods
from util.images.card import Card, CardTab

from ..common import fetch_images


async def format(extra: ExtraGoods) -> Callable[[Card], None]:
  images = await fetch_images(*(i.image for i, _ in zip(extra.goods, range(5))))

  def appender(card: Card) -> None:
    try:
      source = extra.title[extra.title.index("来自") + 2:]
    except ValueError:
      source = "会员购"
    title = f"{source}商品" if len(extra.goods) == 1 else f"{len(extra.goods)} 个{source}商品"
    content = (
      f"{textutil.escape(extra.goods[0].name)}\n"
      f"<span color='#00aeec'>{textutil.escape(extra.goods[0].price)}</span> 起"
    ) if len(extra.goods) == 1 else ""
    width = (
      len(images) * 100 + max(len(images) - 1, 0) * 8
      if len(extra.goods) <= 5 else 600
    )
    image = Image.new("RGBA", (width, 100))
    for i, im in enumerate(images):
      x = i * 108
      image.paste((255, 255, 255), (x, 0, x + 100, 100))
      imutil.paste(image, im.resize((100, 100), imutil.resample()), (x, 0))
    if len(extra.goods) > 5:
      textutil.paste(image, (566, 50), f"+{len(extra.goods) - 5}", "sans", 32, anchor="mm")
    card.add(CardTab(content, title, image))

  return appender
