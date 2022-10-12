from loguru import logger

try:
  from . import plugin  # noqa
except ImportError as e:
  logger.warning(f"{__package__} 缺失依赖: {e}")
