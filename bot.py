import argparse
import os
from typing import Any, Dict

import nonebot
import yaml
from nonebot.adapters.onebot.v11 import Adapter

from util import configs, importing, log

parser = argparse.ArgumentParser()
parser.add_argument("--export-html")
args = parser.parse_args()

bot_config: Dict[str, Any] = {}
if os.path.exists("configs/nonebot.yaml"):
  with open("configs/nonebot.yaml") as f:
    bot_config = yaml.load(f, configs.SafeLoader)

log.init()
nonebot.init(**bot_config, apscheduler_autostart=True)
nonebot.get_driver().register_adapter(Adapter)
importing.load_plugins()

if args.export_html:
  from util import help, permission
  commands = help.CategoryItem.ROOT.html(False)
  index = help.export_index_html()
  permissions = permission.export_html()
  with open(args.export_html, "w") as f:
    f.write((
      "<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
      f"<h2>命令帮助</h2>{commands}<h2>命令大纲</h2>{index}<h2>已知权限节点</h2>{permissions}"
    ))
  print("已导出所有命令帮助和权限节点")
else:
  nonebot.run()
