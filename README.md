# QOI-Decode
A Python implementation of the qoi spec for decoding. (https://qoiformat.org)

## Setup
Clone the repository and run `pip install -r requirements.txt`. You're done!

## Usage
There are two ways to use this program:
### Using QOI-Decode as a module
Example usage:
```py
from decoder import QOIDecoder

image = QOIDecoder('path/to/image.qoi')
# You can access image metadata from this object immediately
image_metadata = [image.width, image.height, image.channels, image.colorspace]
# The image is not decoded until it is being written to disk.
image.write_to('dest/image.png') # You can use any image format supported by Pillow
```
### Using QOI-Decode as a command line utility
Run `decode.py` and enter the QOI image's path and your destination path including the image name and format as instructed by the prompts.

## Notes
The program spends much of its time calculating indeces for the running array. Since the function is purely math, it appears that we are limited by Python's speed. Using [Numba](https://numba.pydata.org) and adding an `@njit` decorator on the `calc_pixel_idx` function leads to a significant performance improvement but has been left out of the repository to simplify setup.
