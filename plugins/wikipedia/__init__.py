from loguru import logger

from .config import CONFIG

if CONFIG.zim:
  try:
    from . import plugin
  except ImportError:
    logger.warning("没有安装libzim，不能使用维基百科插件")
else:
  logger.info("没有提供ZIM文件，将不会加载维基百科插件")
