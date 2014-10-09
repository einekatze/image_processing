from io import BytesIO
from struct import pack
from zlib import crc32, compress
from math import floor
from functools import reduce
from ctypes import c_byte


class PngWriter(object):
    """PngWriter is a class that allows you to encode PNG files."""

    def __init__(self, stream, width, height, dynamic_filtering=True):
        """Creates a new PngWriter object.

        @param BytesIO stream: The stream to write the PNG to.
        @param int width: The width of the resulting image.
        @param int height: The height of the resulting image.
        @param bool dynamic_filtering: Whether dynamic filtering should be used (optional).
        """
        self.stream = stream
        self.width = width
        self.height = height
        self.dynamic_filtering = dynamic_filtering

    def write_signature(self):
        """Writes the PNG signature to the stream."""
        self.stream.write(b"\x89PNG\x0D\x0A\x1A\x0A")
        pass

    def write_ihdr(self):
        """Writes the IHDR chunk to the stream.

        This class only supports creating 8-bit RGB images without interlacing."""

        # width, height, 8-bit bit depth, truecolor, compression method 0, filter method 0, no interlacing.
        data = pack("!2I5b", self.width, self.height, 8, 2, 0, 0, 0)
        self.write_chunk(b"IHDR", data)

    def write_actl(self, num_frames, num_plays):
        """Writes a fcTL chunk to the stream. This chunk is used in APNGs for defining how many frames the animation
        has and how many times it should loop.

        @param int num_frames: The number of frames in this animation. This must equal the count of fcTL chunks.
        @param int num_plays: The number of times to loop this APNG. 0 indicates infinite looping.
        """
        data = pack("!2I", num_frames, num_plays)
        self.write_chunk(b"acTL", data)

    def write_fctl(self, seq, delay_num, delay_den):
        """Writes a fcTL chunk to the stream. This chunk is responsible for defining how frame ``seq`` should be
        displayed in an APNG file. As this class does not support using smaller images as frames, frames are always
        overlaid over the previous frame. The delay is specified as a fraction.

        @param int seq: The sequence number of the frame that this fcTL chunk describes.
        @param int delay_num: The numerator for the fraction representing the frame's delay.
        @param int delay_den: The denominator for the fraction representing the frame's delay.
        """
        # See: https://wiki.mozilla.org/APNG_Specification#.60fcTL.60:_The_Frame_Control_Chunk
        data = pack("!5I2H2B", seq, self.width, self.height, 0, 0, delay_num, delay_den, 0, 0)
        self.write_chunk(b"fcTL", data)

    def write_idat(self, image):
        """Writes an IDAT chunk to the stream. The passed data object is automatically filtered and compressed.

        @param bytes image: A bytes object containing self.height * self.width pixels. Pixels consist of three bytes
                            specifying a 24-bit RGB color.
        """
        self.write_chunk(b"IDAT", self.process_image_data(image))

    def write_fdat(self, seq, image):
        """Writes a fdAT chunk to the stream. The passed data object is automatically filtered and compressed.

        @param int seq: Sequence number of this animation chunk, starting from 0.
        @param bytes image: A bytes object containing self.height * self.width pixels. Pixels consist of three bytes
                            specifying a 24-bit RGB color.
        """
        self.write_chunk(b"fdAT", pack("!I", seq) + self.process_image_data(image))

    def write_iend(self):
        """Writes the IEND chunk to the stream."""
        self.write_chunk(b"IEND")

    def write_chunk(self, type, data=b""):
        """Writes a chunk to the stream.

        @param bytes type: The chunk type identifier (e.g. b"IHDR").
        @param bytes data: The data to be stored in this chunk (optional).
        """
        head = pack("!I4s", len(data), type)
        self.stream.write(head)
        self.stream.write(data)

        # Compute and append the checksum. This is the same as crc32(type + data).
        tail = pack("!I", crc32(data, crc32(type)))
        self.stream.write(tail)

    def write_image(self, image):
        """Convenience method to quickly write a valid PNG image.

        @param bytes image: A bytes object containing self.height * self.width pixels. Pixels consist of three bytes
                            specifying a 24-bit RGB color.
        """
        self.write_signature()
        self.write_ihdr()
        self.write_idat(image)
        self.write_iend()

    def process_image_data(self, image):
        """Filters and compresses the passed image, making it ready to be inserted into a chunk as data.

        @param bytes image: A bytes object containing self.height * self.width pixels. Pixels consist of three bytes
                            specifying a 24-bit RGB color.
        @return bytes: The filtered and compressed data.
        """
        if len(image) != self.width * self.height * 3:
            raise ValueError("Passed data object does not contain %d x %d pixels." % (self.width, self.height))

        # To encode a PNG image, the image first needs to be split up into scanlines for filtering purposes.
        # A filtering mode must be specified for each scanline, so we extract the scanlines first.
        scanlines = [image[i:i + self.width * 3] for i in range(0, self.width * self.height * 3, self.width * 3)]
        processed = []

        if self.dynamic_filtering:
            # Apply dynamic filtering.
            # We use the "minimum sum of absolute differences" heuristic for each scanline to determine the most
            # the filter that allows best compression. See here: http://www.libpng.org/pub/png/book/chapter09.html
            filters = [self.none_filter, self.sub_filter, self.up_filter, self.average_filter, self.paeth_filter]
            min_sum_of_abs_diff = lambda line: reduce(lambda x, y: x + abs(c_byte(y).value), line[1:])

            for i in range(self.height):
                line = scanlines[i]
                previous_line = None if i == 0 else scanlines[i - 1]

                results = []
                for filter_ in filters:
                    processed_line = filter_(line, previous_line)
                    score = min_sum_of_abs_diff(processed_line)
                    results.append((processed_line, score))

                # Sort results by the sum, asc. The filtered line with the lowest sum of absolute differences is picked.
                ranking = sorted(results, key=lambda t: t[1])
                processed.append(ranking[0][0])
        else:
            for i in range(self.height):
                line = scanlines[i]
                previous_line = None if i == 0 else scanlines[i - 1]
                processed.append(self.paeth_filter(line, previous_line))

        # Merge the filtered scanlines, then compress them.
        return compress(b"".join(processed), 9)

    def none_filter(self, scanline, prev_scanline=None):
        """Filters the given scanline using the None filter function. The filter type byte is automatically added.
        @param bytes scanline: The scanline to process.
        @param prev_scanline: The previous scanline. If this parameter is None, then it is assumed that ``scanline``
                              is the first scanline.
        @type prev_scanline: bytes or None
        @return bytes: The new scanline, which will be one byte longer than ``scanline``.
        """

        new_scanline = bytearray()
        new_scanline.append(0)
        new_scanline.extend(scanline)

        return bytes(new_scanline)

    def sub_filter(self, scanline, prev_scanline=None):
        """Filters the given scanline using the Sub filter function. The filter type byte is automatically added.
        @param bytes scanline: The scanline to process.
        @param prev_scanline: The previous scanline. If this parameter is None, then it is assumed that ``scanline``
                              is the first scanline.
        @type prev_scanline: bytes or None
        @return bytes: The new scanline, which will be one byte longer than ``scanline``.
        """

        new_scanline = bytearray(1 + len(scanline))
        new_scanline[0] = 1

        for i, x in enumerate(scanline):
            a = 0 if i < 3 else scanline[i - 3]
            new_scanline[i + 1] = (x - a) % 256

        return bytes(new_scanline)

    def up_filter(self, scanline, prev_scanline=None):
        """Filters the given scanline using the Up filter function. The filter type byte is automatically added.
        @param bytes scanline: The scanline to process.
        @param prev_scanline: The previous scanline. If this parameter is None, then it is assumed that ``scanline``
                              is the first scanline.
        @type prev_scanline: bytes or None
        @return bytes: The new scanline, which will be one byte longer than ``scanline``.
        """

        new_scanline = bytearray(1 + len(scanline))
        new_scanline[0] = 2

        for i, x in enumerate(scanline):
            b = prev_scanline[i] if prev_scanline else 0
            new_scanline[i + 1] = (x - b) % 256

        return bytes(new_scanline)

    def average_filter(self, scanline, prev_scanline=None):
        """Filters the given scanline using the Average filter function. The filter type byte is automatically added.
        @param bytes scanline: The scanline to process.
        @param prev_scanline: The previous scanline. If this parameter is None, then it is assumed that ``scanline``
                              is the first scanline.
        @type prev_scanline: bytes or None
        @return bytes: The new scanline, which will be one byte longer than ``scanline``.
        """

        new_scanline = bytearray(1 + len(scanline))
        new_scanline[0] = 3

        for i, x in enumerate(scanline):
            a = 0 if i < 3 else scanline[i - 3]
            b = prev_scanline[i] if prev_scanline else 0
            avg = floor((a + b) / 2)
            new_scanline[i + 1] = (x - avg) % 256

        return bytes(new_scanline)

    def paeth_filter(self, scanline, prev_scanline):
        """Filters the given scanline using the Paeth filter function. The filter type byte is automatically added.
        @param bytes scanline: The scanline to process.
        @param prev_scanline: The previous scanline. If this parameter is None, then it is assumed that ``scanline``
                              is the first scanline.
        @type prev_scanline: bytes or None
        @return bytes: The new scanline, which will be one byte longer than ``scanline``.
        """

        new_scanline = bytearray(1 + len(scanline))
        new_scanline[0] = 4

        for i, x in enumerate(scanline):
            # Determine the values of corresponding bytes surrounding our byte x.
            # The corresponding byte is always offset by the count of bytes per pixel because we only want to look at
            # at bytes for the same color.
            # So if we are dealing with a red pixel, a, b, c are arranged around x as follows:  c.. b..
            #                                                                                   a.. x..

            a = 0 if i < 3 else scanline[i - 3]

            if prev_scanline:
                b = prev_scanline[i]
                c = 0 if i < 3 else prev_scanline[i - 3]
            else:
                b, c = 0, 0

            # Do Paeth filtering for x, saving the predictor in pr.
            p = a + b - c
            pa = abs(p - a)
            pb = abs(p - b)
            pc = abs(p - c)

            if pa <= pb and pa <= pc:
                pr = a
            elif pb <= pc:
                pr = b
            else:
                pr = c

            # We want to insert the new x after the filter type byte, hence offset 1.
            new_scanline[i + 1] = (x - pr) % 256

        return bytes(new_scanline)
