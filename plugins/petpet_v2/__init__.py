from util import help

from . import (
  alike, angel, anya, asciiart, ask, away, away2, bite, blue, china, coupon, cover, cxk,
  decent_kiss, dianzhongdian, disc, distracted, eat, fisheye, follow, forever, friend, getout,
  hammer, hit, indihome, interview, intimate, jiujiu, kidnap, kiss, knock, laptop, louvre, love,
  lying, marry, message, mirror, need, ori, pad, paint, painter, pat, perfect, petpet, play, police,
  police2, pound, protogen, prpr, punch, rip, roll, rub, safe_sense, shock, slap, spin, suck,
  support, teach, think, throw, throw2, trash, tv, wallpaper, wantwant, watermelon, why_at_me, wife,
  windows, work, worship)

category = help.CategoryItem.find("petpet_v2", True)
category.brief = "梗图生成器"
category.add(help.StringItem("特别感谢: nonebot-plugin-petpet、lab.magiconch.com"))
category.add(help.StringItem("标有[动]的可以传入动图"))
