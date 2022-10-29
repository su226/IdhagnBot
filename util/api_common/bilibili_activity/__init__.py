from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Sequence, TypeVar, overload

from util import util

try:
  import grpc

  from .protos.bilibili.app.dynamic.v2.dynamic_pb2 import (
    DynamicItem, DynamicType, DynDetailsReply, DynDetailsReq, DynModuleType, DynSpaceReq,
    DynSpaceRsp
  )
  from .protos.bilibili.app.dynamic.v2.dynamic_pb2_grpc import DynamicStub
  GRPC_AVAILABLE = True
except ImportError:
  GRPC_AVAILABLE = False

if TYPE_CHECKING:
  from .protos.bilibili.app.dynamic.v2.dynamic_pb2 import DynamicType, Module  # noqa 

Modules = dict["DynModuleType.V", "Module"]

LIST_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space" \
  "?host_mid={uid}&offset={offset}"
DETAIL_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail" \
  "?id={id}"
LIST_API_OLD = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history" \
  "?host_uid={uid}&offset_dynamic_id={offset}"
DETAIL_API_OLD = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail" \
  "?dynamic_id={id}"
GRPC_API = "grpc.biliapi.net"
GRPC_METADATA = (
  ("x-bili-device-bin", b""),
)


async def grpc_fetch(uid: int, offset: str = "") -> tuple[Sequence[DynamicItem], str | None]:
  async with grpc.aio.secure_channel(GRPC_API, grpc.ssl_channel_credentials()) as channel:
    stub = DynamicStub(channel)
    req = DynSpaceReq(host_uid=uid, history_offset=offset)
    res: DynSpaceRsp = await stub.DynSpace(req, metadata=GRPC_METADATA)
  next_offset = res.history_offset if res.has_more else None
  return res.list, next_offset


async def json_fetch(uid: int, offset: str = "") -> tuple[list[dict], str | None]:
  if offset is None:
    offset = ""
  http = util.http()
  async with http.get(LIST_API.format(uid=uid, offset=offset)) as response:
    data = await response.json()
  next_offset = data["data"]["offset"] if data["data"]["has_more"] else None
  return data["data"]["items"], next_offset


@overload
async def grpc_get(id: str) -> DynamicItem: ...


@overload
async def grpc_get(id: list[str]) -> list[DynamicItem]: ...


async def grpc_get(id: str | list[str]) -> DynamicItem | list[DynamicItem]:
  islist = isinstance(id, list)
  if islist:
    ids = ",".join(id)
  else:
    ids = id
  async with grpc.aio.secure_channel(GRPC_API, grpc.ssl_channel_credentials()) as channel:
    stub = DynamicStub(channel)
    req = DynDetailsReq(dynamic_ids=ids)
    res: DynDetailsReply = await stub.DynDetails(req, metadata=GRPC_METADATA)
  if islist:
    return list(res.list)
  return res.list[0]


async def json_get(id: str) -> dict:
  http = util.http()
  async with http.get(DETAIL_API.format(id=id)) as response:
    data = await response.json()
  return data["data"]["item"]


class Content:
  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> Content:
    raise NotImplementedError

  @staticmethod
  def json_parse(item: dict) -> Content:
    raise NotImplementedError


@dataclass
class ContentText(Content):
  text: str

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentText:
    return ContentText(modules[DynModuleType.module_desc].module_desc.text)

  @staticmethod
  def json_parse(item: dict) -> ContentText:
    return ContentText(item["modules"]["module_dynamic"]["desc"]["text"])


@dataclass
class Image:
  src: str
  width: int
  height: int
  size: float


@dataclass
class ContentImage(Content):
  text: str
  images: list[Image]

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentImage:
    return ContentImage(
      modules[DynModuleType.module_desc].module_desc.text,
      [Image(
        image.src,
        image.width,
        image.height,
        image.size,
      ) for image in modules[DynModuleType.module_dynamic].module_dynamic.dyn_draw.items],
    )

  @staticmethod
  def json_parse(item: dict) -> ContentImage:
    module = item["modules"]["module_dynamic"]
    return ContentImage(
      module["desc"]["text"],
      [Image(
        image["src"],
        image["width"],
        image["height"],
        image["size"],
      ) for image in module["major"]["draw"]["items"]]
    )


@dataclass
class ContentVideo(Content):
  text: str
  avid: int
  bvid: str
  title: str
  desc: str | None
  cover: str
  view: int | None
  duration: int
  width: int | None
  height: int | None
  formatted_view: str
  formatted_danmaku: str

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentVideo:
    video = modules[DynModuleType.module_dynamic].module_dynamic.dyn_archive
    if DynModuleType.module_desc in modules:
      text = modules[DynModuleType.module_desc].module_desc.text
    else:
      text = ""
    return ContentVideo(
      text,
      video.avid,
      video.bvid,
      video.title,
      None,
      video.cover,
      video.view,
      video.duration,
      video.dimension.width,
      video.dimension.height,
      video.cover_left_text_2.removesuffix("观看"),
      video.cover_left_text_3.removesuffix("弹幕")
    )

  @staticmethod
  def json_parse(item: dict) -> ContentVideo:
    module = item["modules"]["module_dynamic"]
    video = module["major"]["archive"]
    duration_text: str = video["duration_text"]
    try:
      duration_seg = duration_text.split(":")
      if len(duration_seg) == 2:
        h = 0
        m, s = duration_seg
      else:
        h, m, s = duration_seg
      duration = int(h) * 3600 + int(m) * 60 + int(s)
    except ValueError:
      duration = -1
    return ContentVideo(
      module["desc"]["text"] if module["desc"] is not None else "",
      video["aid"],
      video["bvid"],
      video["title"],
      video["desc"],
      video["cover"],
      None,
      duration,
      None,
      None,
      video["stat"]["play"],
      video["stat"]["danmaku"],
    )


@dataclass
class ContentArticle(Content):
  '''
  专栏
  https://www.bilibili.com/audio/au<ID>
  '''
  id: int
  title: str
  desc: str
  covers: list[str]
  formatted_view: str

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentArticle:
    article = modules[DynModuleType.module_dynamic].module_dynamic.dyn_article
    return ContentArticle(
      int(item.extend.business_id),
      article.title,
      article.desc,
      list(article.covers),
      article.label
    )

  @staticmethod
  def json_parse(item: dict) -> ContentArticle:
    major = item["modules"]["module_dynamic"]["major"]["article"]
    return ContentArticle(
      major["id"],
      major["title"],
      major["desc"],
      major["covers"],
      major["label"],
    )


@dataclass
class ContentAudio(Content):
  '''
  音频
  https://www.bilibili.com/audio/au<ID>
  '''
  id: int
  title: str
  desc: str | None
  cover: str
  label: str

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentAudio:
    audio = modules[DynModuleType.module_dynamic].module_dynamic.dyn_music
    return ContentAudio(
      audio.id,
      audio.title,
      None,
      audio.cover,
      audio.label1,
    )

  @staticmethod
  def json_parse(item: dict) -> ContentAudio:
    module = item["modules"]["module_dynamic"]
    audio = module["major"]["music"]
    return ContentAudio(
      audio["id"],
      audio["title"],
      module["desc"]["text"],
      audio["cover"],
      audio["label"],
    )


@dataclass
class ContentPGC(Content):
  '''
  番剧、电视剧、电影、纪录片等PGC（Professional Generated Content，专业生产内容，与之相对的是
  User Generated Content，用户生产内容，就是UP主上传的视频、专栏等）
  https://www.bilibili.com/bangumi/media/md<SSID> # 介绍页
  https://www.bilibili.com/bangumi/play/ss<SSID> # 播放第一集
  https://www.bilibili.com/bangumi/play/ep<EPID> # 播放指定集
  '''
  ssid: int
  epid: int
  season_name: str
  episode_name: str
  season_cover: str | None
  episode_cover: str
  label: str | None
  formatted_view: str
  formatted_danmaku: str
  duration: int | None
  width: int | None
  height: int | None

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentPGC:
    pgc = modules[DynModuleType.module_dynamic].module_dynamic.dyn_pgc
    return ContentPGC(
      pgc.season_id,
      pgc.epid,
      pgc.season.title,
      pgc.title,
      None,
      pgc.cover,
      None,
      pgc.cover_left_text_2,
      pgc.cover_left_text_3,
      pgc.duration,
      pgc.dimension.width,
      pgc.dimension.height,
    )

  @staticmethod
  def json_parse(item: dict) -> ContentPGC:
    author = item["modules"]["module_author"]
    pgc = item["modules"]["module_dynamic"]["major"]["pgc"]
    return ContentPGC(
      pgc["season_id"],
      pgc["epid"],
      author["name"],
      pgc["title"],
      author["face"],
      pgc["cover"],
      author["label"],
      pgc["stat"]["play"],
      pgc["stat"]["danmaku"],
      None,
      None,
      None,
    )


TContent = TypeVar("TContent", bound=Content)


@dataclass
class ContentForward(Content, Generic[TContent]):
  text: str
  activity: "Activity[TContent] | None"

  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentForward:
    if DynModuleType.module_dynamic in modules:
      original = Activity.grpc_parse(
        modules[DynModuleType.module_dynamic].module_dynamic.dyn_forward.item
      )
    else:
      original = None  # 源动态失效
    return ContentForward(
      modules[DynModuleType.module_desc].module_desc.text,
      original,
    )

  @staticmethod
  def json_parse(item: dict) -> ContentForward:
    if item["orig"]["type"] == "DYNAMIC_TYPE_NONE":
      original = None  # 源动态失效
    else:
      original = Activity.json_parse(item["orig"])
    return ContentForward(
      item["modules"]["module_dynamic"]["desc"]["text"],
      original,
    )


class ContentUnknown(Content):
  @staticmethod
  def grpc_parse(item: DynamicItem, modules: Modules) -> ContentUnknown:
    return ContentUnknown()

  @staticmethod
  def json_parse(item: dict) -> ContentUnknown:
    return ContentUnknown()


GRPC_CONTENT_TYPES: dict["DynamicType.V", type[Content]] = {}
if GRPC_AVAILABLE:
  GRPC_CONTENT_TYPES = {
    DynamicType.word: ContentText,
    DynamicType.draw: ContentImage,
    DynamicType.av: ContentVideo,
    DynamicType.article: ContentArticle,
    DynamicType.music: ContentAudio,
    DynamicType.pgc: ContentPGC,
    DynamicType.forward: ContentForward,
  }
JSON_CONTENT_TYPES: dict[str, type[Content]] = {
  "word": ContentText,
  "draw": ContentImage,
  "av": ContentVideo,
  "article": ContentArticle,
  "music": ContentAudio,
  "pgc": ContentPGC,
  "forward": ContentForward,
}


@dataclass
class Activity(Generic[TContent]):
  uid: int
  name: str
  avatar: str
  id: str
  top: bool
  type: str
  content: TContent
  repost: int | None
  like: int | None
  reply: int | None
  time: int | None

  @staticmethod
  def grpc_parse(item: DynamicItem) -> Activity:
    modules = {module.module_type: module for module in item.modules}
    if DynModuleType.module_author_forward in modules:
      author_module = modules[DynModuleType.module_author_forward].module_author_forward
      uid = author_module.uid
      name = author_module.title[0].text.removeprefix("@")
      avatar = author_module.face_url
      top = False
    else:
      author_module = modules[DynModuleType.module_author].module_author
      uid = author_module.author.mid
      name = author_module.author.name
      avatar = author_module.author.face
      top = author_module.is_top
    if DynModuleType.module_stat_forward in modules:
      stat_module = modules[DynModuleType.module_stat_forward].module_stat_forward
    else:
      stat_module = modules[DynModuleType.module_stat].module_stat
    content_cls = GRPC_CONTENT_TYPES.get(item.card_type, ContentUnknown)
    return Activity(
      uid,
      name,
      avatar,
      item.extend.dyn_id_str,
      top,
      DynamicType.Name(item.card_type),
      content_cls.grpc_parse(item, modules),
      stat_module.like,
      stat_module.repost,
      stat_module.reply,
      None,
    )

  @staticmethod
  def json_parse(item: dict) -> Activity:
    modules = item["modules"]
    author_module = modules["module_author"]
    top = "module_tag" in modules and modules["module_tag"]["text"] == "置顶"
    if "module_stat" in modules:
      stat_module = modules["module_stat"]
      repost = stat_module["forward"]["count"]
      like = stat_module["like"]["count"]
      reply = stat_module["comment"]["count"]
    else:
      repost = None
      like = None
      reply = None
    type = item["type"].removeprefix("DYNAMIC_TYPE_").lower()
    content_cls = JSON_CONTENT_TYPES.get(type, ContentUnknown)
    return Activity(
      author_module["mid"],
      author_module["name"],
      author_module["face"],
      item["id_str"],
      top,
      type,
      content_cls.json_parse(item),
      like,
      repost,
      reply,
      author_module["pub_ts"],
    )
