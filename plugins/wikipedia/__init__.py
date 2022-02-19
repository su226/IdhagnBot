from .config import CONFIG
from nonebot.log import logger

if CONFIG.zim:
  from . import plugin as _
else:
  logger.info("没有提供ZIM文件，将不会加载维基百科插件")
