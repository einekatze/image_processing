from image_processing.canvas import Canvas, RgbaColor


class Font(object):
    """The Font class offers support for writing text onto a Canvas."""

    def __init__(self):
        self.charmap = {}
        self.char_height = 0
        self.char_width = 0

    def load(self, path, charmap, char_width, char_height):
        """Imports a font file.

        @param str path: The path of the font file.
        @param str charmap: The character map.
        @param int char_width: The width of a character.
        @param int char_height: The height of a character.
        """
        if char_width <= 0 or char_height <= 0:
            raise ValueError("Character dimensions must be positive and non-zero.")

        dim_x, dim_y = len(charmap) * char_width, char_height
        canvas = Canvas(dim_x, dim_y, RgbaColor(0, 0, 0, 0))

        with open(path, "rb") as f:
            canvas.import_rgba_data(f.read())

        for i, c in enumerate(charmap):
            self.charmap[c] = canvas.rect(i * char_width, 0, char_width, char_height)

        self.char_width = char_width
        self.char_height = char_height

    def write(self, target, x, y, text):
        """Writes a string of text onto the given canvas.

        @param Canvas target: The canvas to write the text onto.
        @param int x: The x coordinate of where to write the text.
        @param int x: The y coordinate of where to write the text.
        @param str text: The text to write.
        """

        x_offset = 0
        y_offset = 0

        for c in text:
            if c in self.charmap:
                letter = self.charmap[c]
                target.blend(letter, x + x_offset, y + y_offset)
                x_offset += self.char_width
            elif c == "\n":
                x_offset = 0
                y_offset += self.char_height + 2
            else:
                x_offset += self.char_width

