from loguru import logger

from .config import CONFIG

try:
  import libzim
  import pyppeteer
except ImportError:
  logger.warning("没有安装libzim或pyppeteer，不能使用维基百科插件")
else:
  if CONFIG.zim:
    from . import plugin
  else:
    logger.info("没有提供ZIM文件，将不会加载维基百科插件")
