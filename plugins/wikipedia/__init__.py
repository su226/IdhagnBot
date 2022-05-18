from .config import CONFIG
from nonebot.log import logger

if CONFIG.zim:
  try:
    from . import plugin as _
  except ImportError:
    logger.warning("没有安装libzim，不能使用维基百科插件")
else:
  logger.info("没有提供ZIM文件，将不会加载维基百科插件")
