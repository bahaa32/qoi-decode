import io
from fastenum import Enum
import numpy as np
from PIL import Image

RUNNING_ARRAY_LENGTH = 64

class Header:
    def __init__(self, header_bytes: bytes):
        self.magic = header_bytes[:4]
        if self.magic != b"qoif":
            raise Exception("Incorrect magic byte in header (file may be corrupted or not QOI)!")
        self.width = int.from_bytes(header_bytes[4:8], 'big')
        self.height = int.from_bytes(header_bytes[8:12], 'big')
        self.channels = header_bytes[12]
        self.colorspace = header_bytes[13]

# Stores the bit value of the tag in the format (value, mask)
class Tags(Enum):
    rgb   = (0b11111110, 0b11111111)
    rgba  = (0b11111111, 0b11111111)
    index = (0b00000000, 0b11000000)
    diff  = (0b01000000, 0b11000000)
    luma  = (0b10000000, 0b11000000)
    run   = (0b11000000, 0b11000000)

##
# HELPER FUNCTIONS
##
def unpack_deltas(byte):
    return ((byte & 0b00110000) >> 4) - 2, \
           ((byte & 0b00001100) >> 2) - 2, \
           (byte & 0b00000011) - 2

def unpack_luma(first_byte, second_byte):
    dg = (first_byte & 0b00111111) - 32
    dr = ((second_byte & 0b11110000) >> 4) - 8 + dg
    db = (second_byte & 0b00001111) - 8 + dg
    return dr, dg, db

def wrap(num):
    if num < 0:
        return 256 + num
    if num > 255:   
        return num - 256
    return num

def calc_pixel_idx(pixel):
    r, g, b, a = pixel
    return (r * 3 + g * 5 + b * 7 + a * 11) % RUNNING_ARRAY_LENGTH
# END HELPER FUNCTIONS

def read_tag(byte):
    for tag in Tags:
        value, mask = tag.value
        # Mask byte and check for equivalence
        if ((byte & mask) ^ value) == 0:
            return tag
    return None

class QOIDecoder:
    def __init__(self, filename):
        self.header = None
        self.decoded_rgb = None
        self.filename = filename

    def process(self, filename: str):
        with open(filename, 'rb') as file:
            self.header = Header(file.read(14))
            self.decode_file(file)

    def decode_file(self, file: io.BufferedReader):
        decoded_rgb = np.empty((self.header.height * self.header.width + 8, 4), dtype=np.uint8)
        running_array = np.zeros((RUNNING_ARRAY_LENGTH, 4), dtype=np.uint8)
        prev_pixel = np.array([0, 0, 0, 255], dtype=np.uint8)
        curr_idx = 0
        # Start processing!
        # All 'pixels' values are guaranteed to be numpy arrays
        while (curr_byte := file.read(1)):
            curr_byte = curr_byte[0]
            tag = read_tag(curr_byte)
            if tag == Tags.rgb:
                pixels = np.append(
                    np.frombuffer(file.read(3), dtype=np.uint8),
                     prev_pixel[3])
            elif tag == Tags.rgba:
                pixels = np.frombuffer(file.read(4), dtype=np.uint8)
            elif tag == Tags.index:
                # Use the pixel in the running array based on the 6-bit idx
                pixels = running_array[curr_byte & 0b00111111]
            elif tag == Tags.diff:
                dr, dg, db = unpack_deltas(curr_byte)
                # Wraparound pixel values after calculating
                pixels = np.fromiter(map(wrap, [prev_pixel[0] + dr, prev_pixel[1] +
                         dg, prev_pixel[2] + db, prev_pixel[3]]), dtype=np.uint8)
            elif tag == Tags.luma:
                 # Wraparound pixel values after calculating
                dr, dg, db = unpack_luma(curr_byte, file.read(1)[0])
                pixels = np.fromiter(map(wrap, [prev_pixel[0] + dr, prev_pixel[1] +
                         dg, prev_pixel[2] + db, prev_pixel[3]]), dtype=np.uint8)
            elif tag == Tags.run:
                # Repeats the pixel run_length + 1 times
                run_length = (curr_byte & 0b00111111) + 1
                pixels = np.tile(prev_pixel, reps = (run_length, 1))
            else:
                raise Exception("Invalid pixel value")
            # End processing
            decoded_rgb[curr_idx : curr_idx + (pixels.size // 4)] = pixels
            prev_pixel = decoded_rgb[curr_idx]
            runarr_idx = calc_pixel_idx(prev_pixel)
            running_array[runarr_idx] = prev_pixel
            curr_idx += pixels.size // 4
        self.decoded_rgb = np.reshape(decoded_rgb[:-8], (self.header.height, self.header.width, 4))

    def write_to(self, filename):
        self.process(self.filename)
        data = Image.fromarray(self.decoded_rgb, 'RGBA')
        data.save(filename)

def main():
    # Simple CLI for if we're run directly
    input_path = input("QOI image path: ")
    output_path = input("Output path (specify any PIL-supported image format): ")
    decoder = QOIDecoder(input_path)
    decoder.write_to(output_path)

main()
