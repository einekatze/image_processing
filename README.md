# image_processing

image_processing is an experiment in tinkering with images in Python 3 without making use of third-party libraries.
 
This project features a simple PNG encoder, as well as a class for tinkering with 32-bit RGBA images.
Furthermore, primitive font rendering support is available through the Font class. 

image_processing is not a serious attempt at making an image processing library. That's why it only supports 
exporting one single kind of PNG image: 24-bit RGB without interlacing.


## Example application

This project comes with an example application, `example.py`.  Run it to generate an image at out/test.png.


## Creating images for use with image_processing

To create an image that be get used by Canvas' `load_rgb_data` or `load_rgba_data` methods, use GIMP.

Open an image file with GIMP, then choose "Export As..." in the File menu. Open up the collapsible "Select File Type"
list and select "Raw image data". Then, export the image with RGB Save Type "Standard (R,G,B)".

Make sure that the image you are exporting does not contain an alpha channel when you plan to use `load_rgb_data`,
and conversely, make sure an alpha channel exists when using `load_rgba_data`. Furthermore, make sure that the image 
is not indexed. 

Due to the lack of any metadata in this format, your Canvas must be initialized with the correct width and height.
Implementing [PPM](http://en.wikipedia.org/wiki/Netpbm_format#PPM_example) support would fix this issue.


## Attribution 

The [mig68000][bfp] font used in this package was created by [Marc Russell][pix].

[bfp]: http://opengameart.org/content/bitmap-font-pack
[pix]: http://www.spicypixel.net