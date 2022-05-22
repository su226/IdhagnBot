import subprocess as sp
from dataclasses import dataclass


@dataclass
class Info:
  unknown: bool
  model: str
  percent: int
  mem_percent: int
  clk: int
  temp: int


UEVENT_FILE = "uevent"


def read(card: str) -> Info:
  root = f"/sys/class/drm/{card}/device/"
  pci = None
  with open(root + UEVENT_FILE) as f:
    for i in f:
      if i.startswith("PCI_SLOT_NAME="):
        pci = i[14:-1]
        break
  if pci is None:
    raise RuntimeError(f"无法获取PCI槽：{card}")
  proc = sp.run(["lspci", "-s", pci], capture_output=True, text=True)
  model = proc.stdout
  model = model[model.find(": ") + 2: -9]
  return Info(True, model, 0, 0, 0, 0)
