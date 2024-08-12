from io import BytesIO
from typing import Any

import cairo
import gi
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from util import command, misc, textutil

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

TOP_X = 70
TOP_Y = 0
BOTTOM_X = 250
BOTTOM_Y = 130
GRAD_OFFSET = 15


def render_top(cr: "cairo.Context[Any]", layout: Pango.Layout) -> None:
  cr.set_matrix(cairo.Matrix(1, 0, -0.45, 1, 0, 0))

  cr.set_source_rgb(0, 0, 0)
  cr.set_line_width(22)
  cr.move_to(TOP_X + 4, TOP_Y + 4)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, 24, 0, 122)
  grad.add_color_stop_rgb(0.0, 0.0, 0.058823529411764705, 0.1411764705882353)
  grad.add_color_stop_rgb(0.10, 1.0, 1.0, 1.0)
  grad.add_color_stop_rgb(0.18, 0.21568627450980393, 0.22745098039215686, 0.23137254901960785)
  grad.add_color_stop_rgb(0.25, 0.21568627450980393, 0.22745098039215686, 0.23137254901960785)
  grad.add_color_stop_rgb(0.5, 0.7843137254901961, 0.7843137254901961, 0.7843137254901961)
  grad.add_color_stop_rgb(0.75, 0.21568627450980393, 0.22745098039215686, 0.23137254901960785)
  grad.add_color_stop_rgb(0.85, 0.09803921568627451, 0.0784313725490196, 0.12156862745098039)
  grad.add_color_stop_rgb(0.91, 0.9411764705882353, 0.9411764705882353, 0.9411764705882353)
  grad.add_color_stop_rgb(0.95, 0.6509803921568628, 0.6862745098039216, 0.7607843137254902)
  grad.add_color_stop_rgb(1.0, 0.19607843137254902, 0.19607843137254902, 0.19607843137254902)
  cr.set_source(grad)
  cr.set_line_width(20)
  cr.move_to(TOP_X + 4, TOP_Y + 4)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  cr.set_source_rgb(0, 0, 0)
  cr.set_line_width(16)
  cr.move_to(TOP_X, TOP_Y)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, 20, 0, 100)
  grad.add_color_stop_rgb(0.0, 0.9921568627450981, 0.9450980392156862, 0.0)
  grad.add_color_stop_rgb(0.25, 0.9607843137254902, 0.9921568627450981, 0.7333333333333333)
  grad.add_color_stop_rgb(0.4, 1.0, 1.0, 1.0)
  grad.add_color_stop_rgb(0.75, 0.9921568627450981, 0.8588235294117647, 0.03529411764705882)
  grad.add_color_stop_rgb(0.9, 0.4980392156862745, 0.20784313725490197, 0.0)
  grad.add_color_stop_rgb(1.0, 0.9529411764705882, 0.7686274509803922, 0.043137254901960784)
  cr.set_source(grad)
  cr.set_line_width(10)
  cr.move_to(TOP_X, TOP_Y)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  cr.set_line_width(6)
  cr.set_source_rgb(0, 0, 0)
  cr.move_to(TOP_X + 2, TOP_Y - 3)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()
  cr.set_source_rgb(1, 1, 1)
  cr.move_to(TOP_X, TOP_Y - 3)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, 20 + GRAD_OFFSET, 0, 100 + GRAD_OFFSET)
  grad.add_color_stop_rgb(0.0, 1.0, 0.39215686274509803, 0.0)
  grad.add_color_stop_rgb(0.5, 0.4823529411764706, 0.0, 0.0)
  grad.add_color_stop_rgb(0.51, 0.9411764705882353, 0.0, 0.0)
  grad.add_color_stop_rgb(1.0, 0.0196078431372549, 0.0, 0.0)
  cr.set_source(grad)
  cr.set_line_width(4)
  cr.move_to(TOP_X, TOP_Y - 3)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, 20 + GRAD_OFFSET, 0, 100 + GRAD_OFFSET)
  grad.add_color_stop_rgb(0.0, 0.9019607843137255, 0.0, 0.0)
  grad.add_color_stop_rgb(0.5, 0.4823529411764706, 0.0, 0.0)
  grad.add_color_stop_rgb(0.51, 0.9411764705882353, 0.0, 0.0)
  grad.add_color_stop_rgb(1.0, 0.0196078431372549, 0.0, 0.0)
  cr.set_source(grad)
  cr.move_to(TOP_X, TOP_Y - 3)
  PangoCairo.show_layout(cr, layout)


def render_bottom(cr: "cairo.Context[Any]", layout: Pango.Layout):
  cr.set_matrix(cairo.Matrix(1, 0, -0.45, 1, 0, 0))

  cr.set_source_rgb(0, 0, 0)
  cr.set_line_width(22)
  cr.move_to(BOTTOM_X + 5, BOTTOM_Y + 2)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, BOTTOM_Y + 20 + GRAD_OFFSET, 0, BOTTOM_Y + 118 + GRAD_OFFSET)
  grad.add_color_stop_rgb(0, 0.0, 0.058823529411764705, 0.1411764705882353)
  grad.add_color_stop_rgb(0.25, 0.9803921568627451, 0.9803921568627451, 0.9803921568627451)
  grad.add_color_stop_rgb(0.5, 0.5882352941176471, 0.5882352941176471, 0.5882352941176471)
  grad.add_color_stop_rgb(0.75, 0.21568627450980393, 0.22745098039215686, 0.23137254901960785)
  grad.add_color_stop_rgb(0.85, 0.09803921568627451, 0.0784313725490196, 0.12156862745098039)
  grad.add_color_stop_rgb(0.91, 0.9411764705882353, 0.9411764705882353, 0.9411764705882353)
  grad.add_color_stop_rgb(0.95, 0.6509803921568628, 0.6862745098039216, 0.7607843137254902)
  grad.add_color_stop_rgb(1, 0.19607843137254902, 0.19607843137254902, 0.19607843137254902)
  cr.set_source(grad)
  cr.set_line_width(19)
  cr.move_to(BOTTOM_X + 5, BOTTOM_Y + 2)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  cr.set_source_rgb(0.06274509803921569, 0.09803921568627451, 0.22745098039215686)
  cr.set_line_width(17)
  cr.move_to(BOTTOM_X, BOTTOM_Y)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  cr.set_source_rgb(0.8666666666666667, 0.8666666666666667, 0.8666666666666667)
  cr.set_line_width(8)
  cr.move_to(BOTTOM_X, BOTTOM_Y)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, BOTTOM_Y + 20 + GRAD_OFFSET, 0, BOTTOM_Y + 100 + GRAD_OFFSET)
  grad.add_color_stop_rgb(0.0, 0.06274509803921569, 0.09803921568627451, 0.22745098039215686)
  grad.add_color_stop_rgb(0.03, 1.0, 1.0, 1.0)
  grad.add_color_stop_rgb(0.08, 0.06274509803921569, 0.09803921568627451, 0.22745098039215686)
  grad.add_color_stop_rgb(0.2, 0.06274509803921569, 0.09803921568627451, 0.22745098039215686)
  grad.add_color_stop_rgb(1.0, 0.06274509803921569, 0.09803921568627451, 0.22745098039215686)
  cr.set_source(grad)
  cr.set_line_width(7)
  cr.move_to(BOTTOM_X, BOTTOM_Y)
  PangoCairo.layout_path(cr, layout)
  cr.stroke()

  grad = cairo.LinearGradient(0, BOTTOM_Y + 20 + GRAD_OFFSET, 0, BOTTOM_Y + 100 + GRAD_OFFSET)
  grad.add_color_stop_rgb(0.0, 0.9607843137254902, 0.9647058823529412, 0.9725490196078431)
  grad.add_color_stop_rgb(0.15, 1.0, 1.0, 1.0)
  grad.add_color_stop_rgb(0.35, 0.7647058823529411, 0.8352941176470589, 0.8627450980392157)
  grad.add_color_stop_rgb(0.5, 0.6274509803921569, 0.7450980392156863, 0.788235294117647)
  grad.add_color_stop_rgb(0.51, 0.6274509803921569, 0.7450980392156863, 0.788235294117647)
  grad.add_color_stop_rgb(0.52, 0.7686274509803922, 0.8431372549019608, 0.8705882352941177)
  grad.add_color_stop_rgb(1.0, 1.0, 1.0, 1.0)
  cr.set_source(grad)
  cr.move_to(BOTTOM_X, BOTTOM_Y - 3)
  PangoCairo.show_layout(cr, layout)


def render(top: str, bottom: str) -> MessageSegment:
  top_layout = textutil.layout(top, "sans bold", 100)
  bottom_layout = textutil.layout(bottom, "serif bold", 100)
  top_width = top_layout.get_pixel_size()[0]
  bottom_width = bottom_layout.get_pixel_size()[0]
  width = max(top_width + TOP_X, bottom_width + BOTTOM_X - 60)
  if bottom:
    height = 290
  else:
    height = 145
  with cairo.ImageSurface(cairo.FORMAT_RGB24, width, height) as surface:
    cr = cairo.Context(surface)
    cr.rectangle(0, 0, width, height)
    cr.set_source_rgb(1, 1, 1)
    cr.fill()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    render_top(cr, top_layout)
    if bottom:
      render_bottom(cr, bottom_layout)
    f = BytesIO()
    surface.write_to_png(f)
    return MessageSegment.image(f)


choyen = (
  command.CommandBuilder("meme_word.5000choyen", "5000兆元", "兆元", "5000choyen", "choyen")
  .category("meme_word")
  .brief("生成想要5000兆元风格文字")
  .usage("/5000兆元 <红色文本> [银色文本]")
  .build()
)
@choyen.handle()
async def handle_choyen(args: Message = CommandArg()):
  text = args.extract_plain_text().split()
  if len(text) == 2:
    top, bottom = text
  elif len(text) == 1:
    top = text[0]
    bottom = ""
  else:
    await choyen.finish(choyen.__doc__)
  await choyen.finish(await misc.to_thread(render, top, bottom))
