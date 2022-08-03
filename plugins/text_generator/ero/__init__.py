from loguru import logger

try:
  import jieba
except ImportError:
  logger.warning("没有安装jieba，不能使用text_generator.ero")
else:
  from . import plugin
