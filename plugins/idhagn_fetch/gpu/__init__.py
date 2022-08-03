import os
import re
import sys

from . import amd, nvidia
from .common import Info
from .common import read as read_unknown

VENDORS = {
  # 0x8086: intel,
  0x10de: nvidia,
  0x1002: amd
}


def get_gpu_info() -> list[Info]:
  if sys.platform != "linux":
    return []
  gpus = [i for i in os.listdir("/sys/class/drm") if re.match(r"^card\d+$", i)]
  result = []
  for i in gpus:
    with open(f"/sys/class/drm/{i}/device/vendor") as f:
      vendor = int(f.read()[2:-1], 16)
    try:
      result.append(VENDORS[vendor].read(i))
    except Exception:
      result.append(read_unknown(i))
  return result
