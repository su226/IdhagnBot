import cairo
from PIL import Image

with cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10) as surface:
  cr = cairo.Context(surface)
  cr.move_to(0, 0)
  cr.line_to(10, 10)
  cr.stroke()
  Image.frombytes("RGBa", (10, 10), surface.get_data()).save("test.png")
