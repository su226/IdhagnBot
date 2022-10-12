from loguru import logger

from . import upside_down  # noqa

try:
  from . import ero  # noqa
except ImportError as e:
  logger.warning(f"{__package__}.ero 缺失依赖: {e}")
