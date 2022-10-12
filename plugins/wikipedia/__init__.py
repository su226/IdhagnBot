from loguru import logger

from .config import CONFIG

if CONFIG.zim:
  try:
    from . import plugin  # noqa
  except ImportError as e:
    logger.warning(f"{__package__} 缺失依赖: {e}")
else:
  logger.info("没有提供ZIM文件，将不会加载维基百科插件")
