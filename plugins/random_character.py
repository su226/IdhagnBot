import hashlib
import random
from typing import List, Tuple

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg

from util import command, context

ITEMS: List[Tuple[str, List[str]]] = [
  ("角色", [
    "修女", "女仆", "医生/护士", "学生", "人偶", "天使", "兽娘", "恶魔", "精灵", "亡灵", "法师",
    "史莱姆", "OL",
  ]),
  ("性格", ["内向", "元气", "阴郁", "病娇", "迷糊", "笨蛋", "知性", "色欲", "大姐头", "傲娇"]),
  ("主色", [
    "红色", "黑色", "白色", "紫色", "绿色", "黄色", "蓝色", "灰色", "橙色", "青色", "随意",
  ]),
  ("武器", [
    "单手剑", "长戟/枪", "现代枪", "斧头", "镰刀", "锤子", "武士刀", "弓", "双剑", "巨剑", "扫把",
    "伞", "书", "弩", "钓鱼竿", "铲子", "旗帜", "玩偶", "棒球套装", "盾牌", "物理学圣剑", "吉他",
    "御币", "爪子", "舰装", "匕首", "砍刀", "法杖",
  ]),
  ("身体", [
    "机械手", "眼镜", "翅膀", "机械腿", "帽子", "丝袜", "面具", "比基尼", "眼罩", "破烂的衣服",
    "大裙摆", "角", "机械尾巴", "伤痕", "小麦色皮肤",
  ]),
  ("配件", [
    "骷髅", "机械钟", "火焰", "轮椅", "扑克", "锁链", "月亮", "动物", "糖果", "冰", "灯", "棺材",
    "背包", "滑板", "花", "耳机",
  ]),
  ("胸部", ["巨乳", "贫乳", "普通"]),
  ("发型", ["披肩长发", "中短发", "双马尾", "单马尾", "丸子头", "卷发", "杂乱发型", "麻花辫"]),
  ("身高", ["大高个", "萝莉", "普通"]),
]

random_character = (
  command.CommandBuilder("random_character", "随机人设", "人设")
  .usage("/随机人设 [名字]\n默认使用QQ昵称")
  .build())


@random_character.handle()
async def handle_random_character(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
  name = arg.extract_plain_text().rstrip()
  if not name:
    try:
      info = await bot.get_group_member_info(
        group_id=context.get_event_context(event), user_id=event.user_id)
      name = info["card"] or info["nickname"]
    except ActionFailed:
      info = await bot.get_stranger_info(user_id=event.user_id)
      name = info["nickname"]
  rand = random.Random(int.from_bytes(hashlib.md5(name.encode()).digest(), "little"))
  segments = [name]
  for name, choices in ITEMS:
    segments.append(f"{name}: {rand.choice(choices)}")
  await random_character.finish("\n".join(segments))
