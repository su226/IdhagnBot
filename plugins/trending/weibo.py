from typing import Any
from aiohttp import ClientSession
from .common import Item, strip_html

API = "https://weibo.com/ajax/statuses/hot_band"
IMG = "https://wx4.sinaimg.cn/large/{}.jpg"
SEARCH = "https://s.weibo.com/weibo?q=%23{}%23"

def get_image(data: Any) -> str:
  try: return IMG.format(data["mblog"]["pic_ids"][0])
  except: pass
  try: return data["mblog"]["page_info"]["page_pic"]
  except: pass
  return ""

async def get_data() -> list[Item]:
  async with ClientSession() as http:
    response = await http.get(API)
    data = await response.json()
  result = []
  i = data["data"]["hotgov"]
  result.append(Item(
    url=i["url"],
    title="置顶|" + i["word"].strip("#"),
    image=get_image(i),
    content=strip_html(i["mblog"]["text"])
  ))
  for i in data["data"]["band_list"]:
    if i.get("is_ad", 0):
      continue
    label = i["label_name"]
    if label:
      label += "|"
    word = i["word"]
    hot = round(i["raw_hot"] / 10000, 1)
    result.append(Item(
      url=SEARCH.format(word),
      title=label + word,
      image=get_image(i),
      content=f"{hot}万热度|" + strip_html(i["mblog"]["text"])
    ))
  return result
