import sys
import os.path as path
from time import process_time

from image_processing.canvas import Canvas, RgbaColor
from image_processing.font import Font


base_path   = path.abspath(sys.path[0])
input_path  = lambda name: path.join(base_path, "data", name)
output_path = lambda name: path.join(base_path, "out", name)

print("Doing fancy image processing...")
start_time = process_time()

canvas = Canvas(256, 256, RgbaColor(0, 0, 0, 1))
canvas.load_rgb_data(input_path("background-256-256.data"))

foreground = Canvas(96, 64, RgbaColor(0, 0, 0, 0))
foreground.load_rgba_data(input_path("overlay-96-64.data"))

canvas.blend(foreground, 32, 32)
canvas.blend(foreground, 64, 64)
canvas.blend(foreground, 96, 96)
canvas.blend(foreground, -48, 224)

font = Font()
charmap = """ !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}"""
font.load(input_path("mig68000_8x16.data"), charmap, 8, 16)
font.write(canvas, 8, 176, "Hello world!\nThis is a test!")
font.write(canvas, 4, 0, "Long string is long! " * 8)

rect = canvas.rect(8, 176, 24, 32)
canvas.blend(rect, 160, 176)

canvas.to_png(output_path("test.png"))

end_time = process_time()
print("Done in %.3f seconds! Output written to ./out/test.png." % (end_time - start_time))