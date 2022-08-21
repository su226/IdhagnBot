from loguru import logger

try:
  import cv2
except ImportError:
  logger.warning("没有安装opencv-python-headless，不能使用petpet_v2.fisheye")
else:
  from . import plugin
