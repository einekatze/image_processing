from struct import pack, unpack_from
from copy import copy
from math import floor

from image_processing.png_writer import PngWriter


class RgbaColor(object):
    """RgbaColor represents RGBA colors using float values from 0 to 1 inclusive."""

    def __init__(self, r, g, b, a):
        if r < 0. or r > 1.:
            raise ValueError("r must be within the range 0 to 1 inclusive.")
        if g < 0. or g > 1.:
            raise ValueError("g must be within the range 0 to 1 inclusive.")
        if b < 0. or b > 1.:
            raise ValueError("b must be within the range 0 to 1 inclusive.")
        if a < 0. or a > 1.:
            raise ValueError("a must be within the range 0 to 1 inclusive.")

        self.r = float(r)
        self.g = float(g)
        self.b = float(b)
        self.a = float(a)


class Canvas(object):
    """Canvas is a class that represents a 32-bit RGBA image that can be manipulated and drawn upon."""

    def __init__(self, width, height, bgcolor):
        self.width = width
        self.height = height
        self.bgcolor = bgcolor
        self.canvas = []
        self.clear()

    def clear(self):
        """Clears the canvas, filling it with the background color."""
        self.canvas = [copy(self.bgcolor) for _ in range(self.width * self.height)]

    def copy(self):
        """Creates a copy of this canvas.
        @return Canvas: A copy of this canvas.
        """
        c = type(self)(self.width, self.height, self.bgcolor)
        c.canvas = [copy(color) for color in self.canvas]
        return c

    def coordinate_to_index(self, x, y):
        """Returns the index for the given coordinates.
        @param int x: The x coordinate.
        @param int y: The y coordinate.
        @return int: The index.
        """
        if x < 0 or x > self.width - 1 \
                or y < 0 or y > self.height - 1:
            raise ValueError("x or y coordinates out of bounds.")

        return x + self.width * y

    def at(self, x, y):
        """Returns the index for the given coordinates.
        @param int x: The x coordinate.
        @param int y: The y coordinate.
        @return RgbaColor: The color.
        """
        return self.canvas[self.coordinate_to_index(x, y)]

    def rect(self, x, y, width, height):
        """Returns a new Canvas that contains a copy of the pixels in the given rectangle.

        @param int x: The x coordinate of the rectangle's top left corner.
        @param int y: The y coordinate of the rectangle's top left corner.
        @param int width: The width of the rectangle, extending to the right from the top left corner.
        @param int height: The height of the rectangle, extending downwards from the top left corner.
        @return canvas:
        """
        if x < 0 or x > self.width - 1 \
                or y < 0 or y > self.height - 1:
            raise ValueError("x or y coordinates out of bounds.")

        if width < 0 or height < 0:
            raise ValueError("Width and height must be positive.")

        if x + width > self.width \
                or y + height > self.height:
            raise ValueError("The rectangle does not fit into the image.")

        rect = Canvas(width, height, copy(self.bgcolor))

        for target_y in range(height):
            for target_x in range(width):
                color = self.at(x + target_x, y + target_y)
                target_i = target_y * width + target_x
                rect.canvas[target_i] = copy(color)

        return rect

    def blend(self, src, offset_x=0, offset_y=0, ignore_src_alpha=False):
        """Blends the ``src`` canvas onto this canvas.

        @param Canvas src: The canvas to blend onto this one.
        @param int offset_x: The X offset to place the source image at.
        @param int offset_y: The Y offset to place the source image at.
        @param bool ignore_src_alpha: Whether blend should ignore the source image's alpha values
                                      and assume it's opaque.
        """

        for i, src_color in enumerate(src.canvas):
            src_x, src_y = i % src.width, i // src.width

            target_x = offset_x + src_x
            target_y = offset_y + src_y

            # Don't blit pixels that are out of bounds.
            if target_x < 0 or target_x > self.width - 1 \
                    or target_y < 0 or target_y > self.height - 1:
                continue

            dst_color = self.canvas[target_y * self.width + target_x]

            if ignore_src_alpha or src_color.a >= 0.999999:
                dst_color.r = src_color.r
                dst_color.g = src_color.g
                dst_color.b = src_color.b
                dst_color.a = src_color.a
            else:
                new_alpha = src_color.a + dst_color.a * (1 - src_color.a)
                dst_color.r = (src_color.r * src_color.a + dst_color.r * dst_color.a * (1 - src_color.a)) / new_alpha
                dst_color.g = (src_color.g * src_color.a + dst_color.g * dst_color.a * (1 - src_color.a)) / new_alpha
                dst_color.b = (src_color.b * src_color.a + dst_color.b * dst_color.a * (1 - src_color.a)) / new_alpha
                dst_color.a = new_alpha

                if dst_color.a < 0.000001:
                    dst_color.r, dst_color.g, dst_color.b, dst_color.a = 0, 0, 0, 0

    def bytes(self):
        """Returns an 24-bit RGB representation of this canvas as a byte array.
        The image gets blended with the background color.

        @return bytes: An 24-bit RGB representation of this canvas.
        """
        data = bytearray(self.width * self.height * 3)

        for i, color in enumerate(self.canvas):
            if color.a >= 0.999:
                data[i*3:i*3 + 3] = pack("!3B", floor(color.r * 255), floor(color.g * 255), floor(color.b * 255))
            else:
                r = floor((color.r * color.a + self.bgcolor.r * (1 - color.a)) * 255)
                g = floor((color.g * color.a + self.bgcolor.g * (1 - color.a)) * 255)
                b = floor((color.b * color.a + self.bgcolor.b * (1 - color.a)) * 255)
                data[i*3:i*3 + 3] = pack("!3B", r, g, b)

        return bytes(data)

    def import_rgb_data(self, data):
        """Imports a 24-bit RGB image from raw data.

        @param bytes data: The image.
        """
        for i in range(0, len(data), 3):
            r, g, b = unpack_from("!3B", data, i)
            r, g, b = r / 255, g / 255, b / 255
            self.canvas[i // 3] = RgbaColor(r, g, b, 1.0)

    def import_rgba_data(self, data):
        """Imports a 32-bit RGBA image from raw data.

        @param bytes data: The image.
        """
        for i in range(0, len(data), 4):
            r, g, b, a = unpack_from("!4B", data, i)
            r, g, b, a = r / 255, g / 255, b / 255, a / 255
            self.canvas[i // 4] = RgbaColor(r, g, b, a)

    def load_rgb_data(self, path):
        """Imports a 24-bit RGB image from a file.

        @param string path: The image path.
        """
        with open(path, "rb") as f:
            return self.import_rgb_data(f.read())

    def load_rgba_data(self, path):
        """Imports a 32-bit RGBA image from a file.

        @param string path: The image path.
        """
        with open(path, "rb") as f:
            return self.import_rgba_data(f.read())

    def to_png(self, path):
        """Convenience method to export a PNG file with the Canvas' contents.

        @param string path: The image path.
        """
        with open(path, "wb") as f:
            w = PngWriter(f, self.width, self.height)
            w.write_image(self.bytes())
