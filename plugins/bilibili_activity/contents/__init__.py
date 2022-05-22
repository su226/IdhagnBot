# 从B站JS里复制的枚举
# 动态有无图片是不同的，为了区分，这里称有图动态为“相簿”，无图动态为“动态”
# 1:       DYNAMIC_TYPE_FORWARD          # 转发（内容由orig_type决定）
# 2:       DYNAMIC_TYPE_DRAW             # 相簿（有图动态）
# 4:       DYNAMIC_TYPE_WORD             # 动态
# 8:       DYNAMIC_TYPE_AV               # 视频
# 64:      DYNAMIC_TYPE_ARTICLE          # 专栏
# 256:     DYNAMIC_TYPE_MUSIC            # [TODO] 音频
# 512:     DYNAMIC_TYPE_PGC              # [TODO] 番剧、电影、纪录片等？
# 1024:    DYNAMIC_TYPE_NONE
# 2048:    DYNAMIC_TYPE_COMMON_SQUARE
# 2049:    DYNAMIC_TYPE_COMMON_VERTICAL
# 4097, 4098, 4099, 4100, 4101: DYNAMIC_TYPE_PGC
# 4200:    DYNAMIC_TYPE_LIVE             # [TODO] 直播预约？
# 4300:    DYNAMIC_TYPE_MEDIALIST        # [TODO] 播放列表？
# 4302:    DYNAMIC_TYPE_COURSES_SEASON
# 4305:    DYNAMIC_TYPE_APPLET
# 4308:    DYNAMIC_TYPE_LIVE_RCMD        # [TODO] 直播录像？
# 4310:    DYNAMIC_TYPE_UGC_SEASON
# 4311:    DYNAMIC_TYPE_SUBSCRIPTION_NEW
# default: DYNAMIC_TYPE_NONE             # noqa

from typing import Any

from . import activity, article, gallery, repost, unknown, video

HANDLERS = {
  1: repost,
  2: gallery,
  4: activity,
  8: video,
  64: article
}


def handle(content: Any) -> str:
  type_id = content["desc"]["type"]
  if type_id in HANDLERS:
    return HANDLERS[type_id].handle(content)
  return unknown.handle(content)
