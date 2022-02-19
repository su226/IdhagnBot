from util.config import BaseModel, BaseConfig, Field
from core_plugins.context.typing import Context
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError, ClientProxyConnectionError
from aiohttp.http import SERVER_SOFTWARE
from typing import Callable, Literal, TypeVar
from nonebot.adapters.onebot.v11 import Message
from nonebot.log import logger
from nonebot.params import CommandArg
import base64
import nonebot

class Site(BaseModel):
  origin: str
  post_url: str
  api_url: str
  array_path: str
  id_path: str
  sample_path: str

presets = {
  "gelbooru": Site( # Gelbooru (https://gelbooru.com)
    origin="https://gelbooru.com",
    post_url="/index.php?page=post&s=view&id={id}",
    api_url="/index.php?page=dapi&s=post&q=index&tags={tags}&limit={limit}&pid={page}&json=1",
    array_path="/array",
    id_path="/id",
    sample_path="/sample_url"
  ),
  "danbooru": Site( # Danbooru (https://danbooru.donmai.us), Safebooru (https://safebooru.donmai.us)
    origin="https://danbooru.donmai.us",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/large_file_url"
  ),
  "konachan": Site( # Konachan R18 (https://konachan.com), Konachan G (https://konachan.net), Yandere (https://yande.re)
    origin="https://konachan.com",
    post_url="/post/show/{id}",
    api_url="/post.json?tags={tags}&limit={limit}&page={page}",
    array_path="/",
    id_path="/id",
    sample_path="/sample_url"
  ),
  "e621": Site( # e621 (https://e621.net), e926 (https://e926.net)
    origin="https://e621.net",
    post_url="/posts/{id}",
    api_url="/posts.json?tags={tags}&limit={limit}&page={page}",
    array_path="/posts",
    id_path="/id",
    sample_path="/sample/url"
  ),
}

EMPTY_PRESET = {
  "origin": None,
  "post_url": None,
  "api_url": None,
  "array_path": None,
  "id_path": None,
  "sample_path": None,
}

class Command(BaseModel):
  command: list[str]
  brief: str = ""
  usage: str = "/{command} <标签> [limit:每页大小] [page:页码]"
  contexts: list[int] = Field(default_factory=list)
  permission: Literal["member", "admin", "owner", "super"] = "member"
  proxy: str | None = None
  user_agent: str = SERVER_SOFTWARE
  preset: str | None = None
  origin: str | None = None
  post_url: str | None = None
  api_url: str | None = None
  array_path: str | None = None
  id_path: str | None = None
  sample_path: str | None = None

  def to_site(self) -> Site:
    preset = EMPTY_PRESET if self.preset is None else presets[self.preset].dict()
    config = self.dict()
    return Site.parse_obj({key: value if config[key] is None else config[key] for key, value in preset.items()})

class Config(BaseConfig):
  __file__ = "image_board"
  default_limit: int = 5
  max_limit: int = 10
  presets: dict[str, Site] = Field(default_factory=dict)
  sites: list[Command] = Field(default_factory=list)

CONFIG = Config.load()
presets.update(CONFIG.presets)

context: Context = nonebot.require("context")

T = TypeVar("T")
class ParseFailed(Exception): pass
def parse_args(args: list[str], template: dict[str, tuple[Callable[[str], T], T]]):
  tags = []
  special = dict(map(lambda x: (x[0], x[1][1]), template.items()))
  encountered = set()
  for arg in args:
    for name, (factory, _) in template.items():
      if arg.startswith(name + ":"):
        if name in encountered:
          raise ParseFailed(f"参数 {name} 出现了多次")
        encountered.add(name)
        try:
          special[name] = factory(arg.split(":", 1)[1])
        except:
          raise ParseFailed(f"参数 {arg} 无效")
        break
    else:
      tags.append(arg)
  return tags, special

def get_by_path(root: dict, path: str):
  nodes = path.split("/")
  for i in filter(len, nodes):
    root = root[i]
  return root

def register(command: Command):
  site = command.to_site()
  HEADERS = {"User-Agent": command.user_agent}
  POST_URL = site.origin + site.post_url
  API_URL = site.origin + site.api_url
  async def handler(message = CommandArg()):
    args = str(message).split()
    try:
      tags, special = parse_args(args, {
        "limit": (int, CONFIG.default_limit),
        "page": (int, 1)
      })
    except ParseFailed as e:
      await matcher.send(str(e))
      return
    if special["limit"] > CONFIG.max_limit:
      await matcher.send(f"最多只能发送 {CONFIG.max_limit} 张图片")
      return
    async with ClientSession(headers=HEADERS) as http:
      try:
        response = await http.get(API_URL.format(tags=" ".join(tags), limit=special["limit"], page=special["page"]), proxy=command.proxy)
      except ClientProxyConnectionError as e:
        await matcher.send(f"别试了我没挂梯子:\n{e}")
        return
      except ClientConnectionError as e:
        await matcher.send(f"网络异常:\n{e}")
        return
      if response.status != 200:
        if response.status == 503:
          await matcher.send("访问过于频繁，请稍后再试")
        else:
          await matcher.send(f"HTTP错误: {response.status}")
        return
      posts = get_by_path(await response.json(), site.array_path)
      if len(posts) == 0:
        await matcher.send("没有结果")
        return
      segments = []
      for post in posts:
        url = POST_URL.format(id=get_by_path(post, site.id_path))
        segments.append(url)
        try:
          response = await http.get(get_by_path(post, site.sample_path), proxy=command.proxy)
          segments.append(f"[CQ:image,file=base64://{base64.b64encode(await response.read())}]")
        except:
          segments.append("预览下载失败")
    await matcher.send(Message("\n".join(segments)))
  matcher = nonebot.on_command(
    command.command[0],
    context.in_context_rule(*command.contexts),
    set(command.command[1:]),
    permission=context.Permission.parse(command.permission),
    handlers=[handler]
  )
  matcher.__cmd__ = command.command
  matcher.__brief__ = command.brief
  matcher.__doc__ = command.usage.format(command=command.command[0])
  matcher.__ctx__ = command.contexts
  return matcher

for site in CONFIG.sites:
  register(site)
