# 从B站JS里复制的枚举（数字编号只在过时API中出现）
# 动态有无图片是不同的，为了区分，这里称有图动态为“相簿”，无图动态为“动态”
# 1:       DYNAMIC_TYPE_FORWARD # 转发（内容由orig_type决定）
# 2:       DYNAMIC_TYPE_DRAW    # 有图动态（相簿）
# 4:       DYNAMIC_TYPE_WORD    # 文字动态
# 8:       DYNAMIC_TYPE_AV      # 视频
# 64:      DYNAMIC_TYPE_ARTICLE # 专栏
# 256:     DYNAMIC_TYPE_MUSIC   # 音频
# 512, 4097, 4098, 4099, 4100, 4101:
#          DYNAMIC_TYPE_PGC     # 番剧、电影、电视剧、纪录片等
# 1024:    DYNAMIC_TYPE_NONE
# 2048:    DYNAMIC_TYPE_COMMON_SQUARE
# 2049:    DYNAMIC_TYPE_COMMON_VERTICAL
# 4200:    DYNAMIC_TYPE_LIVE
# 4300:    DYNAMIC_TYPE_MEDIALIST
# 4302:    DYNAMIC_TYPE_COURSES_SEASON
# 4305:    DYNAMIC_TYPE_APPLET
# 4308:    DYNAMIC_TYPE_LIVE_RCMD
# 4310:    DYNAMIC_TYPE_UGC_SEASON
# 4311:    DYNAMIC_TYPE_SUBSCRIPTION_NEW
# default: DYNAMIC_TYPE_NONE  # noqa

from typing import Any, List

from nonebot.adapters.onebot.v11 import Message

from util.api_common import bilibili_activity

from ..common import Handler
from . import article, audio, forward, image, text, unknown, video

FORMATTERS: List[Handler[Any]] = [
  (bilibili_activity.ContentText, text.format),
  (bilibili_activity.ContentImage, image.format),
  (bilibili_activity.ContentVideo, video.format),
  (bilibili_activity.ContentArticle, article.format),
  (bilibili_activity.ContentAudio, audio.format),
  (bilibili_activity.ContentForward, forward.format),
]


async def format(activity: bilibili_activity.Activity[Any]) -> Message:
  for type, formatter in FORMATTERS:
    if isinstance(activity.content, type):
      return await formatter(activity)
  return await unknown.format(activity)
