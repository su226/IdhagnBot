from loguru import logger

try:
  import psutil
except ImportError:
  logger.warning("没有安装psutil，不能使用idhagnfetch")
else:
  from . import plugin
