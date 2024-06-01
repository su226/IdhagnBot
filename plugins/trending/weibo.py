from typing import List

from util import misc

from .common import Item

API = "https://weibo.com/ajax/statuses/hot_band"
IMG = "https://wx4.sinaimg.cn/large/{}.jpg"
SEARCH = "https://s.weibo.com/weibo?q=%23{}%23"


async def get_data() -> List[Item]:
  http = misc.http()
  async with http.get(API) as response:
    data = await response.json()
  result = []
  i = data["data"]["hotgov"]
  result.append(Item(
    url=i["url"],
    title="置顶|" + i["word"].strip("#"),
    image="",
    content="微博热搜",
  ))
  for i in data["data"]["band_list"]:
    if i.get("is_ad", 0):
      continue
    label = i["label_name"]
    if label:
      label += "|"
    word = i["word"]
    result.append(Item(
      url=SEARCH.format(word),
      title=label + word,
      image="",
      content=f"微博热搜|热度{i['raw_hot']}",
    ))
  return result
