from loguru import logger

try:
  from . import plugin
except ImportError:
  logger.warning("没有安装mctools，不能使用Minecraft服务器插件")
