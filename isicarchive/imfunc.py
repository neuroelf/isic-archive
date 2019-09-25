"""
isicarchive.imfunc

This module provides image helper functions and doesn't have to be
imported from outside the main package functionality (IsicApi).

Functions
---------
color_superpixel
    Paint the pixels belong to a superpixel list in a specific color.
display_image
    Display an image (in a Jupyter notebook!)
image_mix
    Mix two (RGB or gray) image, with either max or blending
lut_lookup
    Color lookup from a table (LUT)
segmentation_outline
    Extract outline from a segmentation mask image
superpixel_outlines
    Extract superpixel (outline) shapes from superpixel map
write_image
    Write an image to file or buffer (bytes)
"""

# specific version for file
__version__ = '0.4.8'


# imports (needed for majority of functions)
from typing import Any, List, Optional, Tuple, Union
import warnings

import numpy

from .vars import ISIC_DICE_SHAPE, ISIC_FUNC_PPI, ISIC_IMAGE_DISPLAY_SIZE_MAX


# color superpixels in an image
def color_superpixels(
    image:Union[numpy.ndarray, Tuple],
    splst:Union[list, numpy.ndarray],
    spmap:numpy.ndarray,
    color:Union[list, numpy.ndarray],
    alpha:Union[float, numpy.float, list, numpy.ndarray] = 1.0,
    almap:numpy.ndarray = None,
    spval:Union[float, numpy.float, list, numpy.ndarray, None] = None,
    copy_image:bool = False) -> numpy.ndarray:
    """
    Paint the pixels belong to a superpixel list in a specific color.

    Parameters
    ----------
    image : numpy.ndarray or 2- or 3-element Tuple with image size
        Image to be colored, if shape tuple, will be all 0 (black)
    splst : list or flat numpy.ndarray
        List of superpixels to color in the image
    spmap : numpy.ndarray
        Mapping array from func.superpixels_map(...)
    color : either a list or numpy.ndarray
        RGB Color code or list of codes to use to color superpixels
    alpha : either float or numpy.float value or None
        Alpha (opacity) value between 0.0 and 1.0, if None, set to 1.0
    spval : optional numpy.ndarray
        Per-pixel opacity value (e.g. confidence, etc.)
    copy_image : bool
        Copy the input image prior to painting, default: False
    
    Returns
    -------
    image : numpy.ndarray
        Image with superpixels painted
    """

    # check inputs
    if isinstance(image, tuple):
        if len(image) == 2 and (isinstance(image[0], int) and
            isinstance(image[1], int)):
            im_shape = image
            image = numpy.zeros(image[0] * image[1], dtype=numpy.uint8)
        elif len(image) == 3 and (isinstance(image[0], int) and
            isinstance(image[1], int) and isinstance(image[2], int) and
            (image[2] == 1 or image[2] == 3)):
            im_shape = image
            image = numpy.zeros(image[0] * image[1] * image[2],
                dtype=numpy.uint8).reshape((image[0] * image[1], image[2]))
        else:
            raise ValueError('Invalid image shape.')
        copy_image = False
    else:
        im_shape = image.shape
    num_cols = im_shape[1]
    has_almap = False
    if not almap is None:
        if almap.size != (im_shape[0] * im_shape[1]):
            raise ValueError('Invalid alpha map.')
        has_almap = True
        am_shape = almap.shape
        try:
            almap.shape = (almap.size,)
        except:
            raise
    if copy_image:
        image = numpy.copy(image)
    if len(im_shape) == 3 or im_shape[1] > 3:
        planes = im_shape[2] if len(im_shape) == 3 else 1
        image.shape = (im_shape[0] * im_shape[1], planes)
    else:
        if len(im_shape) > 1:
            planes = im_shape[1]
        else:
            planes = 1
    has_alpha = False
    if planes > 3:
        planes = 3
        has_alpha = True
    numsp = len(splst)
    if spval is None:
        spval = numpy.ones(numsp, dtype=numpy.float32)
    elif isinstance(spval, float) or isinstance(spval, numpy.float):
        spval = spval * numpy.ones(numsp, dtype=numpy.float32)
    elif len(spval) != numsp:
        spval = numpy.ones(numsp, dtype=numpy.float32)
    if len(color) == 3 and isinstance(color[0], int):
        color = [color] * numsp
    if alpha is None:
        alpha = 1.0
    if isinstance(alpha, float):
        alpha = [alpha] * numsp
    if isinstance(alpha, list):
        if len(alpha) != numsp:
            raise ValueError('alpha list must match number of superpixels')
    sp_skip = 6.0 * numpy.trunc(0.75 + 0.25 * numpy.sqrt([
        im_shape[0] * im_shape[1] / spmap.shape[0]]))[0]
    
    # for each superpixel (index)
    for idx in range(numsp):

        # get pixel indices, compute inverse alpha, and then set pixel values
        spcol = color[idx]
        singlecol = False
        num_colors = 1
        if isinstance(spcol, list):
            if isinstance(spcol[0], int):
                singlecol = True
            else:
                num_colors = len(spcol)
        elif isinstance(spcol, numpy.ndarray):
            if spcol.size == 3:
                singlecol = True
            else:
                num_colors = spcol.shape[0]
        if num_colors > 6:
            num_colors = 6
        spalpha = alpha[idx]
        if isinstance(spalpha, float) and not singlecol:
            spalpha = [spalpha] * num_colors
        spidx = splst[idx]
        spnum = spmap[spidx, -1]
        sppidx = spmap[spidx, 0:spnum]
        if singlecol:
            spalpha = spalpha * spval[idx]
            spinv_alpha = 1.0 - spalpha
            for p in range(planes):
                if spalpha == 1.0:
                    image[sppidx, p] = spcol[p]
                else:
                    image[sppidx, p] = numpy.round(
                        spalpha * spcol[p] + spinv_alpha * image[sppidx, p])
            if has_alpha:
                image[sppidx, 3] = numpy.round(255.0 * 1.0 -
                    (1.0 - 255.0 * image[sppidx, 3]) *
                    (1.0 - 255.0 * spalpha))
            elif has_almap:
                almap[sppidx] = 1.0 - (1.0 - almap[sppidx]) * spinv_alpha
        else:
            sppval = spval[idx]
            if not (isinstance(sppval, list) or isinstance(sppval, numpy.ndarray)):
                sppval = [sppval] * num_colors
            elif len(sppval) < num_colors:
                sppval = [sppval[0]] * num_colors
            sppidxx = sppidx % num_cols
            sppidxy = sppidx // num_cols
            float_num = float(num_colors)
            spcidx = numpy.trunc(0.5 + (sppidxx + sppidxy).astype(numpy.float) *
                (float_num / sp_skip)).astype(numpy.int32) % num_colors
            for cc in range(num_colors):
                spcsel = spcidx == cc
                spcidxxy = sppidxx[spcsel] + sppidxy[spcsel] * num_cols
                spccol = spcol[cc]
                spcalpha = spalpha[cc] * sppval[cc]
                spinv_alpha = 1.0 - spcalpha
                for p in range(planes):
                    if spcalpha == 1.0:
                        image[spcidxxy, p] = spccol[p]
                    else:
                        image[spcidxxy, p] = numpy.round(
                            spcalpha * spccol[p] + spinv_alpha * image[spcidxxy, p])
                if has_alpha:
                    image[spcidxxy, 3] = numpy.round(255.0 * 1.0 -
                        (1.0 - 255.0 * image[spcidxxy, 3]) *
                        (1.0 - 255.0 * spcalpha))
                elif has_almap:
                    almap[spcidxxy] = 1.0 - (1.0 - almap[spcidxxy]) * spinv_alpha
    image.shape = im_shape
    if has_almap:
        almap.shape = am_shape
    return image

# display image
def display_image(
    image_data:Union[bytes, str, numpy.ndarray],
    image_shape:Tuple = None,
    max_size:int = ISIC_IMAGE_DISPLAY_SIZE_MAX,
    library:str = 'matplotlib',
    ipython_as_object:bool = False,
    mpl_axes:object = None,
    **kwargs,
    ) -> Optional[object]:
    """
    Display image in a Jupyter notebook; supports filenames, bytes, arrays

    Parameters
    ----------
    image_data : bytes, str, ndarray/imageio Array
        Image specification (file data, filename, or image array)
    image_shape : tuple
        Image shape (necessary if flattened array!)
    max_size : int
        Desired maximum output size on screen
    library : str
        Either 'matplotlib' (default) or 'ipython'
    mpl_axes : object
        Optional existing matplotlib axes object
    
    No returns
    """

    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    import imageio

    # check inputs
    if image_data is None:
        return
    if not isinstance(library, str):
        raise ValueError('Invalid library selection.')
    library = library.lower()
    if not library in ['ipython', 'matplotlib']:
        raise ValueError('Invalid library selection.')
    if (isinstance(image_data, numpy.ndarray) or
        isinstance(image_data, imageio.core.util.Array)):
        if library == 'ipython':
            try:
                image_data = write_image(image_data, 'buffer', 'jpg')
            except:
                raise
    elif isinstance(image_data, str) and (len(image_data) < 256):
        try:
            with open(image_data, 'rb') as image_file:
                image_data = image_file.read()
        except:
            raise
    if library == 'matplotlib' and isinstance(image_data, bytes):
        try:
            image_data = imageio.imread(image_data)
        except:
            raise
    if not isinstance(max_size, int) or (max_size < 32) or (max_size > 5120):
        max_size = ISIC_IMAGE_DISPLAY_SIZE_MAX
    if image_shape is None:
        try:
            if library == 'ipython':
                image_array = imageio.imread(image_data)
                image_shape = image_array.shape
            else:
                image_shape = image_data.shape
        except:
            raise
    image_height = image_shape[0]
    image_width = image_shape[1]
    image_max_xy = max(image_width, image_height)
    shrink_factor = max(1.0, image_max_xy / max_size)
    image_width = int(image_width / shrink_factor)
    image_height = int(image_height / shrink_factor)

    # depending on library call appropriate function
    if library == 'ipython':
        # IMPORT DONE HERE TO SAVE TIME BETWEEN LIBRARY CHOICES
        from ipywidgets import Image as ipy_Image
        from IPython.display import display as ipy_display
        try:
            image_out = ipy_Image(value=image_data,
                width=image_width, height=image_height)
            if not ipython_as_object:
                ipy_display(image_out)
                return None
            return image_out
        except Exception as e:
            warnings.warn('Problem producing image for display: ' + str(e))
            return None
    else:
        # IMPORT DONE HERE TO SAVE TIME BETWEEN LIBRARY CHOICES
        import matplotlib
        import matplotlib.pyplot as mpl_pyplot
        try:
            display_width = image_width / ISIC_FUNC_PPI
            display_height = image_height / ISIC_FUNC_PPI
            if mpl_axes is None:
                if 'figsize' in kwargs:
                    mpl_pyplot.figure(figsize=kwargs['figsize'])
                else:
                    mpl_pyplot.figure(figsize=(display_width, display_height))
                ax_img = mpl_pyplot.imshow(image_data,
                    interpolation='hanning')
                ax_img.axes.set_axis_off()
                mpl_pyplot.show()
            else:
                mpl_axes.imshow(image_data)
        except Exception as e:
            warnings.warn('Problem producing image for display: ' + str(e))
            return None

# image composition (from other images)
def image_compose(
    imlist:list,
    outsize:Tuple,
    bgcolor:list = [255,255,255],
    ) -> numpy.ndarray:
    if not isinstance(outsize, tuple) and not isinstance(outsize, list):
        raise ValueError('Invalid outsize parameter.')
    if (len(outsize) != 2 or not isinstance(outsize[0], int) or
        not isinstance(outsize[1], int) or outsize[0] < 1 or
        outsize[1] < 1 or (outsize[0] * outsize[2] > 16777216)):
        raise ValueError('Invalid image dimensions in outsize parameter.')
    out = numpy.zeros(3 * outsize[0] * outsize[1], dtype=numpy.uint8).reshape(
        (outsize[1], outsize[0], 3,))
    if (isinstance(bgcolor, tuple) or isinstance(bgcolor, list)) and len(bgcolor) == 3:
        try:
            out[:,:,0] = bgcolor[0]
        except:
            pass
        try:
            out[:,:,1] = bgcolor[1]
        except:
            pass
        try:
            out[:,:,2] = bgcolor[2]
        except:
            pass
    im_shape = out.shape
    for ii in imlist:
        if not isinstance(ii, list) or len(ii) < 3:
            continue
        ii_image = ii[0]
        ii_shape = ii_image.shape
        if len(ii_shape) < 2 or len(ii_shape) > 3:
            continue
        elif len(ii_shape) == 3 and not ii_shape[2] in [1, 3]:
            continue
        ii_x = ii[1]
        ii_y = ii[2]
        if ii_x >= im_shape[1] or ii_y >= im_shape[0]:
            continue
        if len(ii) == 3:
            ii_alpha = 1.0
        else:
            ii_alpha = ii[3]
        if ii_alpha <= 0.0:
            continue
        if ii_alpha > 1.0:
            ii_alpha = 1.0
        if not (isinstance(ii_image, numpy.ndarray) and
            isinstance(ii_x, int) and isinstance(ii_y, int) and
            (isinstance(ii_alpha, float) or (
            isinstance(ii_alpha, numpy.ndarray) and
            ii_alpha.ndim == 2 and ii_alpha.shape[0] == ii_image.shape[0]))):
            continue
        sfrom_x = 0
        sfrom_y = 0
        sto_x = ii_shape[1]
        sto_y = ii_shape[0]
        tfrom_x = ii_x
        tfrom_y = ii_y
        if tfrom_x < 0:
            sfrom_x -= tfrom_x
            tfrom_x = 0
        if tfrom_y < 0:
            sfrom_y -= tfrom_y
            tfrom_y = 0
        from_x = sto_x - sfrom_x
        from_y = sto_y - sfrom_y
        if from_x <= 0 or from_y <= 0:
            continue
        tto_x = tfrom_x + from_x
        tto_y = tfrom_y + from_y
        if tto_x > im_shape[1]:
            shrink = tto_x - im_shape[1]
            tto_x -= shrink
            sto_x -= shrink
        if tto_y > im_shape[0]:
            shrink = tto_y - im_shape[0]
            tto_y -= shrink
            sto_y -= shrink
        if tto_x <= tfrom_x or tto_y <= tfrom_y:
            continue
        if len(ii_shape) == 2:
            if sfrom_x == 0 and sfrom_y == 0 and sto_x == ii_shape[1] and sto_y == ii_shape[0]:
                out[tfrom_y:tto_y, tfrom_x:tto_x, :] = image_mix(
                    out[tfrom_y:tto_y, tfrom_x:tto_x, :], ii_image, ii_alpha)
            else:
                out[tfrom_y:tto_y, tfrom_x:tto_x, :] = image_mix(
                    out[tfrom_y:tto_y, tfrom_x:tto_x, :],
                    ii_image[sfrom_y:sto_y, sfrom_x:sto_x], ii_alpha)
        else:
            if sfrom_x == 0 and sfrom_y == 0 and sto_x == ii_shape[1] and sto_y == ii_shape[0]:
                out[tfrom_y:tto_y, tfrom_x:tto_x, :] = image_mix(
                    out[tfrom_y:tto_y, tfrom_x:tto_x, :], ii_image, ii_alpha)
            else:
                out[tfrom_y:tto_y, tfrom_x:tto_x, :] = image_mix(
                    out[tfrom_y:tto_y, tfrom_x:tto_x, :],
                    ii_image[sfrom_y:sto_y, sfrom_x:sto_x, :], ii_alpha)
    return out

# image correlation (pixel values)
def image_corr(
    im1:numpy.ndarray,
    im2:numpy.ndarray,
    immask:numpy.ndarray = None,
    ) -> float:
    if im1.size != im2.size:
        raise ValueError('Images must match in size.')
    if immask is None:
        cc = numpy.corrcoef(im1.reshape(im1.size), im2.reshape(im2.size))
    else:
        if immask.size != im1.size:
            immask = image_resample(numpy.uint8(255) * immask.astype(numpy.uint8),
                (im1.shape[0], im1.shape[1])) >= 128
        if immask.dtype != numpy.bool:
            immask = (immask > 0)
        cc = numpy.corrcoef(im1[immask], im2[immask])
    return cc[0,1]

# Dice coeffient
def image_dice(
    im1:numpy.ndarray,
    im2:numpy.ndarray,
    immask:numpy.ndarray) -> float:
    if im1.shape != im2.shape:
        if len(im1.shape) > 2:
            if im1.shape[2] != 1:
                raise ValueError('Image cannot have more than 1 plane.')
        if len(im2.shape) > 2:
            if im2.shape[2] != 1:
                raise ValueError('Image cannot have more than 1 plane.')
        if (im1.shape[0], im1.shape[1]) != ISIC_DICE_SHAPE:
            im1 = image_resample(im1, ISIC_DICE_SHAPE)
        if (im2.shape[0], im2.shape[1]) != ISIC_DICE_SHAPE:
            im2 = image_resample(im2, ISIC_DICE_SHAPE)
    if immask is None:
        im1 = (im1.reshape(im1.size) > 0)
        im2 = (im2.reshape(im2.size) > 0)
    else:
        if immask.size != im1.size:
            immask = image_resample(numpy.uint8(255) * immask.astype(numpy.uint8),
                (im1.shape[0], im1.shape[1])) >= 128
        im1 = (im1[immask] > 0)
        im2 = (im2[immask] > 0)
    s1 = numpy.sum(im1)
    s2 = numpy.sum(im2)
    return 2 * numpy.sum(numpy.logical_and(im1, im2)) / (s1 + s2)

# image in gray
def image_gray(image:numpy.ndarray, rgb_format:bool = True) -> numpy.ndarray:
    im_shape = image.shape
    if len(im_shape) < 3:
        if rgb_format:
            if image.dtype != numpy.uint8:
                image = numpy.trunc(255.0 * image).astype(numpy.uint8)
            return image.reshape((im_shape[0], im_shape[1], 1,)).repeat(3, axis=2)
        return image
    p = image[:, :, 0].astype(numpy.float)
    for pc in range(1, min(3, im_shape[2])):
        p += image[:, :, pc].astype(numpy.float)
    p /= numpy.float(min(3, im_shape[2]))
    if rgb_format:
        if image.dtype != numpy.uint8:
            p = numpy.trunc(255.0 * p).astype(numpy.uint8)
        return p.astype(numpy.uint8).reshape(
            (im_shape[0], im_shape[1], 1,)).repeat(3, axis=2)
    return p.astype(image.dtype)

# mark border of an image with "content"
def image_mark_border(
    image:numpy.ndarray,
    content:Union[str,bytes],
    color_diff:int = 24,
    ecc_redundancy_level:float = 0.5,
    pix_width:int = 3,
    border_expand:bool = True,
    ) -> numpy.ndarray:
    """
    Mark image border with content (encoded)

    Parameters
    ----------
    image : ndarray
        RGB or grayscale (uint8) image array
    content : str or bytes array
        Content to be encoded into the image border, if too long for
        selected scheme, warning will be printed and fitting scheme
        selected, if possible (max length=1023 bytes)
    color_diff : int
        Amount by which pixel brightness will differ to signify 0 and 1
    ecc_redundancy_level : float
        Amount of payload bytes that can be missing/damaged
    pix_width:int
        Number of pixels (in each dimension) to use for a marker
    border_expand : bool
        If True (default) expand border by number of pixels

    Returns
    -------
    marked : ndarray
        Image with content encoded into border
    """

    # IMPORT DONE HERE TO SAVE TIME DURING MODULE INIT
    from .reedsolo import RSCodec
    from .sampler import Sampler

    # get some numbers, encode message, copy image
    if not isinstance(content, str) and not isinstance(content, bytes):
        raise ValueError('Invalid content (type).')
    if not isinstance(pix_width, int) or pix_width < 1:
        raise ValueError('Invalid pix_width parameter.')
    im_shape = image.shape
    im_rgb = (len(im_shape) > 2 and im_shape[2] > 2)
    im_y = im_shape[0]
    im_x = im_shape[1]
    if border_expand:
        if im_rgb:
            marked = numpy.zeros(
                (im_y + 2 * pix_width, im_x + 2 * pix_width, im_shape[2],),
                dtype=numpy.uint8)
            marked[0:pix_width,pix_width:im_x+pix_width,:] = image[:pix_width,:,:]
            marked[pix_width:im_y+pix_width,0:pix_width,:] = image[:,:pix_width,:]
            marked[pix_width:im_y+pix_width,pix_width:im_x+pix_width,:] = image
            marked[im_y+pix_width:,pix_width:im_x+pix_width,:] = image[-pix_width:,:,:]
            marked[pix_width:im_y+pix_width,im_x+pix_width:,:] = image[:,-pix_width:,:]
            marked[:pix_width,:pix_width,:] = numpy.trunc(0.5 * (
                marked[:pix_width,pix_width:pix_width+pix_width,:].astype(numpy.float32) +
                marked[pix_width:pix_width+pix_width,:pix_width,:].astype(numpy.float32)))
            marked[-pix_width:,:pix_width,:] = numpy.trunc(0.5 * (
                marked[-2*pix_width:-pix_width,:pix_width,:].astype(numpy.float32) +
                marked[-pix_width:,pix_width:pix_width+pix_width,:].astype(numpy.float32)))
            marked[:pix_width,-pix_width:,:] = numpy.trunc(0.5 * (
                marked[:pix_width,-2*pix_width:-pix_width,:].astype(numpy.float32) +
                marked[pix_width:pix_width+pix_width,-pix_width:,:].astype(numpy.float32)))
            marked[-pix_width:,-pix_width:,:] = numpy.trunc(0.5 * (
                marked[-2*pix_width:-pix_width,-pix_width:,:].astype(numpy.float32) +
                marked[-pix_width:,-2*pix_width:-pix_width,:].astype(numpy.float32)))
        else:
            marked[0:pix_width,pix_width:im_x+pix_width] = image[:pix_width,:]
            marked[pix_width:im_y+pix_width,0:pix_width] = image[:,:pix_width]
            marked[pix_width:im_y+pix_width,pix_width:im_x+pix_width] = image
            marked[im_y+pix_width:,pix_width:im_x+pix_width] = image[-pix_width:,:]
            marked[pix_width:im_y+pix_width,im_x+pix_width:] = image[:,-pix_width:]
            marked[:pix_width,:pix_width] = numpy.trunc(0.5 * (
                marked[:pix_width,pix_width:pix_width+pix_width].astype(numpy.float32) +
                marked[pix_width:pix_width+pix_width,:pix_width].astype(numpy.float32)))
            marked[-pix_width:,:pix_width] = numpy.trunc(0.5 * (
                marked[-2*pix_width:-pix_width,:pix_width].astype(numpy.float32) +
                marked[-pix_width:,pix_width:pix_width+pix_width].astype(numpy.float32)))
            marked[:pix_width,-pix_width:] = numpy.trunc(0.5 * (
                marked[:pix_width,-2*pix_width:-pix_width].astype(numpy.float32) +
                marked[pix_width:pix_width+pix_width,-pix_width:].astype(numpy.float32)))
            marked[-pix_width:,-pix_width:] = numpy.trunc(0.5 * (
                marked[-2*pix_width:-pix_width,-pix_width:].astype(numpy.float32) +
                marked[-pix_width:,-2*pix_width:-pix_width].astype(numpy.float32)))
        im_shape = marked.shape
    else:
        marked = image.copy()
    s = Sampler()
    if im_rgb:
        marked[0:pix_width,:,:] = s.sample_grid(marked[0:pix_width,:,:],
            [list(range(pix_width)), list(range(im_shape[1]))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[:,0:pix_width,:] = s.sample_grid(marked[:,0:pix_width,:],
            [list(range(im_shape[0])), list(range(pix_width))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[-pix_width:,:,:] = s.sample_grid(marked[-pix_width:,:,:],
            [list(range(pix_width)), list(range(im_shape[1]))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[:,-pix_width:,:] = s.sample_grid(marked[:,-pix_width:,:],
            [list(range(im_shape[0])), list(range(pix_width))],
            'gauss' + str(24 * pix_width), out_type='uint8')
    else:
        marked[0:pix_width,:] = s.sample_grid(marked[0:pix_width,:],
            [list(range(pix_width)), list(range(im_shape[1]))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[:,0:pix_width] = s.sample_grid(marked[:,0:pix_width],
            [list(range(im_shape[0])), list(range(pix_width))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[-pix_width:,:] = s.sample_grid(marked[-pix_width:,:],
            [list(range(pix_width)), list(range(im_shape[1]))],
            'gauss' + str(24 * pix_width), out_type='uint8')
        marked[:,-pix_width:] = s.sample_grid(marked[:,-pix_width:],
            [list(range(im_shape[0])), list(range(pix_width))],
            'gauss' + str(24 * pix_width), out_type='uint8')
    im_y = im_shape[0] - 2 * pix_width 
    im_x = im_shape[1] - 2 * pix_width
    num_wrd_y = min(255, im_y // (pix_width * 24))
    num_wrd_x = min(255, im_x // (pix_width * 24))
    capacity = 4 * (num_wrd_y + num_wrd_x - 8)
    if isinstance(content, str):
        content = content.encode('utf-8')
    clen = len(content)
    if clen > 1023:
        raise ValueError('Content too long.')
    slen = int(0.95 + float(clen) * 2.0 * ecc_redundancy_level)
    mlen = clen + slen
    if mlen <= 255:
        cchunks = clen
        nchunks = 1
    else:
        nchunks = 1 + (mlen - 1) // 255
        cchunks = 1 + (clen - 1) // nchunks
        slen = int(0.95 + float(cchunks) * 2.0 * ecc_redundancy_level)
        if (cchunks + slen) > 255:
            nchunks += 1
            cchunks = 1 + (clen - 1) // nchunks
            slen = int(0.95 + float(cchunks) * 2.0 * ecc_redundancy_level)
    if nchunks > 16:
        raise ValueError('ECC factor too high.')
    r = RSCodec(slen)
    b = r.encode_to_bits(content, cchunks)
    if capacity < len(b):
        raise ValueError('Content too long to encode.')
    if len(b) < capacity:
        b0 = b[:]
        while len(b) < capacity:
            b.extend([r.value_to_bits(257)])
            b.extend(b0)

    # mark image with side markers
    bnum = clen // 256
    boff = 4 * (nchunks - 1) + 64 * bnum
    sm0 = r.value_to_bits(0 + boff)
    sm1 = r.value_to_bits(1 + boff)
    sm2 = r.value_to_bits(2 + boff)
    sm3 = r.value_to_bits(3 + boff)
    wm0 = r.value_to_bits(num_wrd_y)
    wm1 = r.value_to_bits(num_wrd_x)
    sm = [[sm0,wm0], [sm0,wm0], [sm1,wm1], [sm1,wm1],
        [sm2,wm0], [sm2,wm0], [sm3,wm1], [sm3,wm1]]
    for cidx in range(8):
        sm[cidx].extend([r.value_to_bits(clen % 256), r.value_to_bits(slen)])
    nwyr = num_wrd_y - 4
    nwxr = num_wrd_x - 4
    nwyc = float(nwyr)
    nwxc = float(nwxr)
    nwy = 0.5 * nwxc
    nwx = 0.5 * nwyc
    lidx = 0
    while nwyr > 0 or nwxr > 0:
        if nwy <= nwx:
            sm[0].append(b[lidx])
            lidx += 1
            sm[1].append(b[lidx])
            lidx += 1
            sm[4].append(b[lidx])
            lidx += 1
            sm[5].append(b[lidx])
            lidx += 1
            nwy += nwxc
            nwyr -= 1
        else:
            sm[2].append(b[lidx])
            lidx += 1
            sm[3].append(b[lidx])
            lidx += 1
            sm[6].append(b[lidx])
            lidx += 1
            sm[7].append(b[lidx])
            lidx += 1
            nwx += nwyc
            nwxr -= 1
    image_mark_pix(marked, 0, pix_width, 0, color_diff, False)
    image_mark_pix(marked, 0, pix_width, im_shape[0]-pix_width, color_diff, False)
    image_mark_pix(marked, 2, pix_width, 0, color_diff, False)
    image_mark_pix(marked, 2, pix_width, im_shape[0]-pix_width, color_diff, False)
    for cidx in range(8):
        side = cidx // 2
        if (side % 2) == 0:
            num_wrd = num_wrd_y
        else:
            num_wrd = num_wrd_x
        for widx in range(num_wrd):
            word = sm[cidx][widx]
            if (cidx % 2) == 0:
                wcrd = widx
            else:
                wcrd = num_wrd + widx
            image_mark_word(marked, side, pix_width, num_wrd, wcrd, color_diff, word)
    return marked

# mark pixel in image (color darker or brighter)
def image_mark_pix(image, side, pix_width, pcrd, value, brighter):
    shape = image.shape
    it = 255 - value
    darker = not brighter
    if side == 0 or side == 2:
        yf = pcrd
        yt = pcrd + pix_width
        if side == 0:
            xf = 0
            xt = pix_width
        else:
            xf = shape[1] - pix_width
            xt = shape[1]
    else:
        xf = pcrd
        xt = pcrd + pix_width
        if side == 1:
            yf = 0
            yt = pix_width
        else:
            yf = shape[0] - pix_width
            yt = shape[0]
    v0 = value
    if len(shape) > 2 and shape[2] == 3:
        v2 = v1 = v0
        m0 = numpy.mean(image[yf:yt,xf:xt,0])
        m1 = numpy.mean(image[yf:yt,xf:xt,1])
        m2 = numpy.mean(image[yf:yt,xf:xt,2])
        if darker and m0 > it:
            v0 += m0 - it
        elif brighter and m0 < value:
            v0 += value - m0
        if darker and m1 > it:
            v1 += m1 - it
        elif brighter and m1 < value:
            v1 += value - m1
        if darker and m2 > it:
            v2 += m2 - it
        elif brighter and m2 < value:
            v2 += value - m2
        if darker:
            (v0, v1, v2) = (-v0, -v1, -v2)
        image[yf:yt,xf:xt,0] = numpy.maximum(0.0, numpy.minimum(255.0,
            image[yf:yt,xf:xt,0].astype(numpy.float) + v0))
        image[yf:yt,xf:xt,1] = numpy.maximum(0.0, numpy.minimum(255.0,
            image[yf:yt,xf:xt,1].astype(numpy.float) + v1))
        image[yf:yt,xf:xt,2] = numpy.maximum(0.0, numpy.minimum(255.0,
            image[yf:yt,xf:xt,2].astype(numpy.float) + v2))
    else:
        m0 = numpy.mean(image[yf:yt,xf:xt])
        if darker and m0 > it:
            v0 += m0 - it
        elif brighter and m0 < value:
            v0 += value - m0
        if darker:
            v0 = -v0
        image[yf:yt,xf:xt] = numpy.maximum(0.0, numpy.minimum(255.0,
            image[yf:yt,xf:xt].astype(numpy.float) + v0))

# mark word (of size 10 "pixels") in image
def image_mark_word(image, side, pix_width, num_wrd, wcrd, value, word):
    shape = image.shape
    if side == 0 or side == 2:
        slen = shape[0]
    else:
        slen = shape[1]
    if wcrd < num_wrd:
        scrd = pix_width * (1 + 12 * wcrd)
        pix_add = pix_width
    else:
        scrd = slen - pix_width * (2 + 12 * (wcrd - num_wrd))
        pix_add = -pix_width
    for i in range(10):
        image_mark_pix(image, side, pix_width, scrd, value, word[i] > 0)
        scrd += pix_add
    image_mark_pix(image, side, pix_width, scrd, 2*value, False)
    scrd += pix_add
    image_mark_pix(image, side, pix_width, scrd, 2*value, True)

# image mixing (python portion)
def image_mix(
    image_1:numpy.ndarray,
    image_2:numpy.ndarray,
    alpha_2:Union[float, numpy.ndarray, None] = 0.5,
    ) -> numpy.ndarray:
    """
    Mix two (RGB and/or grayscale) image with either max or blending

    Parameters
    ----------
    image_1 : ndarray
        First image (2D: gray, 3D: color)
    image_2 : ndarray
        Second image
    alpha_2 : alpha value(s), either float, ndarray, or None
        Blending selection - for a single value, this is the opacity
        of the second image (default = 0.5, i.e. equal mixing); for
        an array, it must match the size, and be a single plane; if
        None, each image component is set to the maximum across the
        two arrays
    
    Returns
    -------
    out_image : ndarray
        Mixed image
    """
    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    from .jitfunc import image_mix as image_mix_jit

    # get original shapes and perform necessary checks and reshaping
    im1shape = image_1.shape
    im1reshape = True
    im2shape = image_2.shape
    im2reshape = True
    if image_1.shape[0] != image_2.shape[0]:
        raise ValueError('Invalid input images.')
    if not alpha_2 is None and isinstance(alpha_2, numpy.ndarray):
        a2shape = alpha_2.shape
        if not alpha_2.dtype is numpy.float32:
            alpha_2 = alpha_2.astype(numpy.float32)
    im1pix = im1shape[0]
    im1planes = 1
    if len(im1shape) > 1:
        if im1shape[1] == 3 and len(im1shape) == 2:
            im1planes = 3
        else:
            im1pix *= im1shape[1]
            if len(im1shape) > 2:
                im1planes = im1shape[2]
    if not im1planes in [1, 3]:
        if im1planes > 3:
            if len(im1shape) == 3:
                image_1 = image_1[:,:,0:3]
            else:
                image_1 = image_1[:,0:3]
            im1planes = 3
            im1reshape = False
        else:
            raise ValueError('Invalid input image_1.')
    im2pix = im2shape[0]
    im2planes = 1
    if len(im2shape) > 1:
        if im2shape[1] == 3 and len(im2shape) == 2:
            im2planes = 3
        else:
            im2pix *= im2shape[1]
            if len(im2shape) > 2:
                im2planes = im2shape[2]
    if not im2planes in [1, 3]:
        if im2planes > 3:
            if len(im2shape) == 3:
                image_2 = image_2[:,:,0:3]
            else:
                image_2 = image_2[:,0:3]
            im2planes = 3
            im2reshape = False
        else:
            raise ValueError('Invalid input image_1.')
        raise ValueError('Invalid input image_2.')
    if im1pix != im2pix:
        raise ValueError('Invalid input images.')
    if isinstance(alpha_2, numpy.ndarray) and alpha_2.size not in [1, im1pix]:
        raise ValueError('Invalid Alpha size.')
    try:
        image_1.shape = (im1pix, im1planes)
    except:
        try:
            image_1 = image_1.reshape((im1pix, im1planes))
        except:
            raise ValueError('Unabled to format image_1.')
    try:
        image_2.shape = (im1pix, im2planes)
    except:
        try:
            image_2 = image_2.reshape((im1pix, im2planes))
        except:
            if im1reshape:
                image_1.shape = im1shape
            raise ValueError('Unabled to format image_2.')
    if not alpha_2 is None:
        if isinstance(alpha_2, float):
            alpha_2 = numpy.float32(alpha_2) * numpy.ones(im1pix,
                dtype=numpy.float32)
            a2shape = alpha_2.shape
        else:
            if alpha_2.size == 1:
                alpha_2 = alpha_2 * numpy.ones(im1pix, dtype=numpy.float32)
                a2shape = alpha_2.shape
            else:
                try:
                    alpha_2.shape = (im1pix)
                except:
                    try:
                        alpha_2 = alpha_2.reshape(im1pix)
                    except:
                        if im1reshape:
                            image_1.shape = im1shape
                        if im2reshape:
                            image_2.shape = im2shape
                        raise ValueError('Unable to format alpha_2.')
    
    # attempt to use JIT function
    try:
        immix = image_mix_jit(image_1, image_2, alpha_2)
    
    # and return original inputs to their previous state in any case!
    except:
        if im1reshape:
            image_1.shape = im1shape
        if im2reshape:
            image_2.shape = im2shape
        if isinstance(alpha_2, numpy.ndarray):
            alpha_2.shape = a2shape
        raise
    if im1reshape:
        image_1.shape = im1shape
    if im2reshape:
        image_2.shape = im2shape
    if not alpha_2 is None:
        alpha_2.shape = a2shape
    if im1shape[-1] in [1, 3]:
        immix.shape = im1shape
    else:
        if len(im1shape) == 3:
            immix.shape = (im1shape[0], im1shape[1], immix.shape[-1])
    return immix

# image resampling (cheap!)
def image_resample(image:numpy.ndarray, new_shape:tuple) -> numpy.ndarray:
    im_shape = image.shape
    if len(im_shape) < 2:
        raise ValueError('Invalid image array.')
    if isinstance(new_shape, int) and new_shape > 1:
        max_shape = max(im_shape)
        sf = float(new_shape) / float(max_shape)
        new_shape = (int(sf * float(im_shape[0])), int(sf * float(im_shape[1])))
    elif isinstance(new_shape, float) and new_shape > 0.0 and new_shape <= 8.0:
        new_shape = (int(new_shape * float(im_shape[0])),
            int(new_shape * float(im_shape[1])))
    if not isinstance(new_shape, tuple) or len(new_shape) != 2:
        raise ValueError('Invalid new_shape parameter')
    if not isinstance(new_shape[0], int) or new_shape[0] < 1:
        raise ValueError('Invalid new_shape[0] value')
    if not isinstance(new_shape[1], int) or new_shape[1] < 1:
        raise ValueError('Invalid new_shape[1] value')

    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    from .jitfunc import image_resample_u1, image_resample_f4

    if len(im_shape) < 3:
        re_shape = (im_shape[0], im_shape[1], 1)
        try:
            image.shape = re_shape
        except:
            raise RuntimeError('Error setting necessary planes in shape.')
    if image.dtype == numpy.uint8:
        rs_image = image_resample_u1(image, new_shape[0], new_shape[1])
    else:
        rs_image = image_resample_f4(image, new_shape[0], new_shape[1])
    rs_shape = rs_image.shape
    if rs_shape[2] == 1:
        rs_image.shape = (rs_shape[0], rs_shape[1])
    return rs_image

# rotate image (90 degrees left, right; or 180 degrees)
def image_rotate(image:numpy.ndarray, how:str = None) -> numpy.ndarray:
    if not how or not isinstance(how, str) or not how[0].lower() in 'flr':
        return image
    im_shape = image.shape
    has_planes = (len(im_shape) > 2)
    how = how[0].lower()
    if how == 'f':
        if has_planes:
            return image[::-1, ::-1, :]
        else:
            return image[::-1, ::-1]
    elif how == 'r':
        if has_planes:
            return numpy.transpose(image, (1, 0, 2,))[:, ::-1, :]
        else:
            return numpy.transpose(image, (1, 0,))[:, ::-1]
    else:
        if has_planes:
            return numpy.transpose(image, (1, 0, 2,))[::-1, :, :]
        else:
            return numpy.transpose(image, (1, 0,))[::-1, :]

# smooth image using fft
def image_smooth_fft(image:numpy.ndarray, fwhm:float) -> numpy.ndarray:

    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    from .jitfunc import conv_kernel

    # deal with invalid/special values
    if fwhm <= 0.0:
        return image
    elif fwhm <= 0.36:
        fwhm = fwhm * numpy.sqrt(float(image.size))
    
    # place kernel into image
    k = conv_kernel(numpy.float(fwhm))
    ki = k.repeat(k.size).reshape((k.size,k.size))
    ki = ki * ki.T
    im_shape = image.shape
    if image.dtype != numpy.uint8:
        from_uint8 = False
        if len(im_shape) < 3:
            ka = numpy.zeros_like(image)
        else:
            ka = numpy.zeros(im_shape[0] * im_shape[1],
                dtype=numpy.float32).reshape((im_shape[0], im_shape[1],))
    else:
        from_uint8 = True
        image = image.astype(numpy.float32)
        ka = numpy.zeros(im_shape[0] * im_shape[1],
            dtype=numpy.float32).reshape((im_shape[0], im_shape[1],))
    kh = ki.shape[0] // 2
    ka[0:kh+1,0:kh+1] = ki[kh:,kh:]
    ka[0:kh+1,-kh:] = ki[kh:,0:kh]
    ka[-kh:,0:kh+1] = ki[0:kh,kh:]
    ka[-kh:,-kh:] = ki[0:kh,0:kh]

    # then perform 2D FFT
    if len(image.shape) < 3:
        out = numpy.fft.ifftn(numpy.fft.fft2(image) * numpy.fft.fft2(ka)).real
    else:
        out = numpy.zeros(image.size, dtype=image.dtype).reshape(image.shape)
        for p in range(image.shape[2]):
            out[:,:,p] = numpy.fft.ifft2(numpy.fft.fft2(image[:,:,p]) * numpy.fft.fft2(ka)).real
    if from_uint8:
        out = numpy.trunc(out).astype(numpy.uint8)
    return out

# color LUT operation
def lut_lookup(
    values:numpy.ndarray,
    pos_lut:numpy.ndarray,
    neg_lut:numpy.ndarray = None,
    default:List = None,
    format:str='ndarray',
    trans_fac:float = 1.0,
    trans_off:float = 0.0,
    above_pos_col:List = None,
    below_neg_col:List = None,
    ):
    if pos_lut.ndim != 2:
        raise ValueError('Invalid LUT')
    elif pos_lut.shape[1] != 3:
        raise ValueError('Invalid LUT')
    num_vals = values.size
    num_cols = pos_lut.shape[0]
    if not neg_lut is None:
        if neg_lut.ndim != 2:
            raise ValueError('Invalid LUT')
        elif neg_lut.shape[1] != 3:
            raise ValueError('Invalid LUT')
        elif neg_lut.shape[0] != num_cols:
            raise ValueError('Negative LUT must match in number of colors')
    if not isinstance(default, list):
        default = [0, 0, 0]
    elif len(default) != 3:
        default = [0, 0, 0]
    else:
        default = [].extend(default)
        if not isinstance(default[0], int) or default[0] < 0:
            default[0] = 0
        elif default[0] > 255:
            default[0] = 255
        if not isinstance(default[1], int) or default[1] < 0:
            default[1] = 0
        elif default[1] > 255:
            default[1] = 255
        if not isinstance(default[2], int) or default[2] < 0:
            default[2] = 0
        elif default[2] > 255:
            default[2] = 255
    if not above_pos_col is None:
        if not isinstance(above_pos_col, list) or len(above_pos_col) != 3:
            raise ValueError('Invalid above_pos_col parameter')
        if (not isinstance(above_pos_col[0], int) or
            not isinstance(above_pos_col[1], int) or
            not isinstance(above_pos_col[2], int) or
            above_pos_col[0] < 0 or above_pos_col[0] > 255 or
            above_pos_col[1] < 0 or above_pos_col[1] > 255 or
            above_pos_col[2] < 0 or above_pos_col[2] > 255):
            raise ValueError('Invalid above_pos_col parameter')
    if not below_neg_col is None:
        if not isinstance(below_neg_col, list) or len(below_neg_col) != 3:
            raise ValueError('Invalid below_neg_col parameter')
        if (not isinstance(below_neg_col[0], int) or
            not isinstance(below_neg_col[1], int) or
            not isinstance(below_neg_col[2], int) or
            below_neg_col[0] < 0 or below_neg_col[0] > 255 or
            below_neg_col[1] < 0 or below_neg_col[1] > 255 or
            below_neg_col[2] < 0 or below_neg_col[2] > 255):
            raise ValueError('Invalid below_neg_col parameter')
    zero = numpy.zeros(1, dtype=values.dtype)
    if trans_fac != 1.0:
        values = trans_fac * values
    else:
        values = values.copy()
    if not neg_lut is None and trans_off > 0:
        vs = numpy.sign(values)
        values = vs * numpy.maximum(zero, numpy.abs(values) - trans_off)
    elif trans_off != 0:
        values = values - trans_off
    if above_pos_col is None:
        values *= float(num_cols - 1)
    else:
        values *= float(num_cols)
    ispos = (values > 0.0)
    if not neg_lut is None:
        isneg = (values < 0.0)
    values = numpy.trunc(values, dtype=numpy.int32)
    colors = numpy.zeros((num_vals, 3), dtype=numpy.uint8, order='C')
    colors[:,0] = default[0]
    colors[:,1] = default[1]
    colors[:,2] = default[2]
    if above_pos_col is None:
        values[values >= num_cols] = num_cols - 1
        colors[ispos, 0] = pos_lut[values[ispos], 0]
        colors[ispos, 1] = pos_lut[values[ispos], 1]
        colors[ispos, 2] = pos_lut[values[ispos], 2]
    else:
        above = (values >= num_cols)
        below = ispos and (not above)
        colors[below, 0] = pos_lut[values[below], 0]
        colors[below, 1] = pos_lut[values[below], 1]
        colors[below, 2] = pos_lut[values[below], 2]
        colors[above, 0] = above_pos_col[0]
        colors[above, 1] = above_pos_col[1]
        colors[above, 2] = above_pos_col[2]
    if neg_lut is None:
        values = -values
        if below_neg_col is None:
            values[values >= num_cols] = num_cols - 1
            colors[isneg, 0] = neg_lut[values[isneg], 0]
            colors[isneg, 1] = neg_lut[values[isneg], 1]
            colors[isneg, 2] = neg_lut[values[isneg], 2]
        else:
            above = (values >= num_cols)
            below = isneg and (not above)
            colors[below, 0] = pos_lut[values[below], 0]
            colors[below, 1] = pos_lut[values[below], 1]
            colors[below, 2] = pos_lut[values[below], 2]
            colors[above, 0] = below_neg_col[0]
            colors[above, 1] = below_neg_col[1]
            colors[above, 2] = below_neg_col[2]
    return colors

# segmentation outline (coordinates, image, or SVG/path)
def segmentation_outline(
    seg_mask:numpy.ndarray,
    out_format:str = 'osvg',
    negative:bool = True,
    path_attrib:str = '',
    ) -> Any:
    """
    Extract segmentation outline (shape path) from segmentation mask

    Parameters
    ----------
    seg_mask : ndarray
        Gray-scale mask with values > 0 being included
    out_format : str
        Format selection:
        'coords' - return a list with 2D coordinates for each outline pixel
        'image'  - return a grayscale image with boundary set to 255
        'osvg'   - outline SVG (along the outer pixel borders) string
        'osvgp'  - return a the SVG path (without SVG container)
    negative : bool
        If true (default), the path describes the non-segmentated part
    path_attrib : str
        Optional path attributes
    
    Returns
    -------
    outline : Any
        Segmentation outline in the selected format
    """

    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    import scipy.ndimage as ndimage

    if not isinstance(out_format, str) or (not out_format in
        ['coords', 'image', 'osvg', 'osvgp']):
        raise ValueError('Invalid out_format.')
    if seg_mask.dtype != numpy.bool:
        seg_mask = seg_mask > 0
    image_shape = seg_mask.shape
    rowlen = image_shape[1]
    if out_format == 'image':
        outline = numpy.zeros(image_shape, dtype=numpy.uint8, order='C')
    if not isinstance(path_attrib, str):
        path_attrib = ''
    ext_mask = numpy.zeros((image_shape[0]+4, rowlen+4), dtype=numpy.bool, order='C')
    ext_mask[2:-2, 2:-2] = seg_mask
    ext_eroded = ndimage.binary_erosion(ext_mask)
    ext_out = ext_mask.copy()
    ext_out[ext_eroded] = False
    if out_format == 'image':
        outline[ext_out[2:-2, 2:-2]] = 255
        return outline
    outcoords = numpy.where(ext_out)
    num_pix = outcoords[0].size
    if out_format == 'coords':
        outline = numpy.concatenate((outcoords[0].reshape((num_pix, 1)),
            outcoords[1].reshape((num_pix, 1))), axis=1) - 2
    else:
        # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
        from .jitfunc import superpixel_path, svg_path_from_list

        if negative:
            neg_path = 'M0 0v{0:d}h{1:d}v-{0:d}h-{1:d}zM'.format(image_shape[0], rowlen)
        else:
            neg_path = 'M'
        svg_path = svg_path_from_list(superpixel_path(num_pix,
            outcoords[0][0], outcoords[1][0], ext_mask)).tostring().decode('utf-8')
        if out_format[-1] != 'p':
            outline = ('<svg id="segmentation" width="{0:d}" height="{1:d}" xmlns="{2:s}">' +
                '<path id="segmentationp" d="{3:s}{4:.1f} {5:.1f}{6:s}z" {7:s} /></svg>').format(
                rowlen, image_shape[0], 'http://www.w3.org/2000/svg',
                neg_path, float(outcoords[1][0])-2.5, float(outcoords[0][0])-2.5,
                svg_path, path_attrib)
        else:
            outline = '<path id="segmentationp" d="{0:s}{1:.1f} {2:.1f}{3:s}z" {4:s} />'.format(
                neg_path, float(outcoords[1][0])-2.5, float(outcoords[0][0])-2.5,
                svg_path, path_attrib)
    return outline

# superpixel Dice
def superpixel_dice(list1:numpy.ndarray, list2:numpy.ndarray) -> float:
    """
    Return the DICE coefficient for two superpixel lists.

    Parameters
    ----------
    list1, list2 : list
        List(s) of superpixels from which to compute DICE coefficient
    
    Returns
    -------
    dice : float
        DICE coefficient
    """
    intersect = numpy.intersect1d(list1, list2)
    return 2.0 * float(intersect.size) / float(len(list1) + len(list2))

# superpixel outlines (coordinates, image, or SVG/paths)
def superpixel_outlines(
    pixel_map:numpy.ndarray,
    image_shape:Tuple = None,
    out_format:str = 'osvgp',
    pix_selection:List = None,
    path_attribs:Union[List,str] = None,
    ) -> dict:
    """
    Extract superpixel outlines (shape paths) from superpixel map

    Parameters
    ----------
    pixel_map : ndarray
        Either an RGB, index, or map of a superpixel image
    image_shape : tuple
        If a map is given, the size of the original image is needed
        to correctly compute the 2D coordinates from the map
    out_format : str
        Format selection:
        'cjson'  - return a contour JSON (list-of-dicts) with item fields
                   "geometry": {"type": "polygon", "coordinates": LIST},
                   "properties": {"labelindex": "INDEX"}
        'coords' - return a dict with 2D coordinates for each superpixel
        'image'  - return a grayscale image with boundaries set to 255
        'osvg'   - outline SVG (along the outer pixel borders) string
        'osvgp'  - return a dict with the osvg paths
        'osvgs'  - return a dict with the osvg paths inside an SVG
        'svg', 'svgp', 'svgs' - same for painting a path along the pixels
    pix_selection : list
        Optional selection of superpixel ids to process
    path_attribs : list
        Optional list with per-superpixel path attributes (for ALL ids!)
    
    Returns
    -------
    outlines : Any
        Superpixel outlines in the selected format
    """

    # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
    import scipy.ndimage as ndimage
    from .jitfunc import superpixel_decode, superpixel_map

    if len(pixel_map.shape) > 2:
        pixel_map = superpixel_decode(pixel_map)
    pix_test = pixel_map[-1,-2]
    if pix_test > 0 and pix_test < 4096:
        image_shape = pixel_map.shape
        pixel_map = superpixel_map(pixel_map)
    elif not isinstance(image_shape, tuple):
        raise ValueError('pixel_map in map format requires image_shape')
    if not isinstance(out_format, str) or (not out_format in
        ['cjson', 'coords', 'image', 'osvg', 'osvgp', 'osvgs', 'svg', 'svgp', 'svgs']):
        raise ValueError('Invalid out_format.')
    rowlen = image_shape[1]
    map_shape = pixel_map.shape
    num_idx = map_shape[0]
    if out_format == 'cjson':

        # IMPORT DONE HERE TO SAVE TIME AT MODULE INIT
        from .jitfunc import superpixel_contour, svg_coord_list

        pix_shapes = []
    elif out_format == 'image':
        pix_shapes = numpy.zeros(image_shape, dtype=numpy.uint8, order='C')
    else:

        # IMPORTS DONE HERE TO SAVE TIME AT MODULE INIT
        if out_format[0] == 'o':
            from .jitfunc import superpixel_path, svg_path_from_list
        elif out_format[0] == 's':
            from .jitfunc import superpixel_outline_dir

        pix_shapes = dict()
        if out_format in ['svg', 'svgp', 'svgs']:
            ddict = {
                1000001:'h1',
                1000999:'h-1',
                1001000:'v1',
                1001001:'h1v1',
                1001999:'v1h-1',
                1999000:'v-1',
                1999001:'v-1h1',
                1999999:'h-1v-1',
                }
    if pix_selection is None:
        pix_selection = range(num_idx)
    if isinstance(path_attribs, str):
        pa = path_attribs
    elif isinstance(path_attribs, list):
        if len(path_attribs) < num_idx:
            raise ValueError('path_attribs must be given for all superpixels.')
    else:
        pa = ''
    minustwo = numpy.int32(-2)
    for idx in pix_selection:
        num_pix = pixel_map[idx,-1]
        pixidx = pixel_map[idx, 0:num_pix]
        ycoords = pixidx // rowlen
        xcoords = pixidx - (rowlen * ycoords)
        minx = numpy.amin(xcoords)
        maxx = numpy.amax(xcoords)
        miny = numpy.amin(ycoords)
        maxy = numpy.amax(ycoords)
        spsx = 1 + maxx - minx
        spsy = 1 + maxy - miny
        spx_map = numpy.zeros((spsy+4, spsx+4), dtype=numpy.bool, order='C')
        spx_map.flat[(xcoords - (minx-2)) + (spsx+4) * (ycoords - (miny-2))] = True
        spx_eroded = ndimage.binary_erosion(spx_map)
        spx_out = spx_map.copy()
        spx_out[spx_eroded] = False
        outcoords = numpy.where(spx_out)
        out_x = outcoords[1][0].astype(numpy.int32)
        out_y = outcoords[0][0].astype(numpy.int32)
        num_pix = outcoords[0].size
        if out_format == 'cjson':
            contour = svg_coord_list(superpixel_contour(
                num_pix, out_y, out_x, spx_map) +
                [minx + out_x + minustwo, miny + out_y + minustwo]
                ).tostring().decode('utf-8')
            pix_shapes.append({
                'geometry': {'type': 'polygon', 'coordinates': contour},
                'properties': {'labelindex': str(idx)}})
        elif out_format == 'coords':
            pix_shapes[idx] = numpy.concatenate((
                outcoords[0].reshape((num_pix, 1)) + (miny-2),
                outcoords[1].reshape((num_pix, 1)) + (minx-2)),
                axis=1).astype(numpy.int32)
        elif out_format == 'image':
            pix_shapes[miny:(miny+spsy), minx:(minx+spsx)] = numpy.maximum(
                pix_shapes[miny:(miny+spsy), minx:(minx+spsx)], numpy.uint8(
                255) * spx_out[2:-2, 2:-2].astype(numpy.uint8))
        elif out_format[0] == 'o':
            svg_path = svg_path_from_list(superpixel_path(
                num_pix, out_y, out_x, spx_map)).tostring().decode('utf-8')
            if isinstance(path_attribs, list):
                pa = path_attribs[idx]
            if out_format[-1] == 's':
                svg = ('<svg id="superpixel_{0:d}" width="{1:d}" height="{2:d}" xmlns="{3:s}">' +
                    '<path id="superpixelp_{4:d}" d="M{5:.1f} {6:.1f}{7:s}z" {8:s} /></svg>').format(
                    idx, rowlen, image_shape[0], 'http://www.w3.org/2000/svg', idx,
                    float(out_x + minx)-2.5, float(out_y + miny)-2.5,
                    svg_path, pa)
            else:
                svg = '<path id="superpixel_{0:d}" d="M{1:.1f} {2:.1f}{3:s}z" {4:s} />'.format(
                    idx, float(out_x + minx)-2.5, float(out_y + miny)-2.5,
                    svg_path, pa)
            pix_shapes[idx] = svg
        else:
            (ycoord, xcoord, out_moves) = superpixel_outline_dir(num_pix, spx_out)
            svg_dirs = [ddict[move] for move in out_moves]
            if isinstance(path_attribs, list):
                pa = path_attribs[idx]
            if out_format[-1] == 's':
                svg = ('<svg id="superpixel_{0:d}" width="{1:d}" height="{2:d}" xmlns="{3:s}">' +
                    '<path id="superpixelp_{4:d}" d="M{5:d} {6:d}{7:s}z" {8:s} /></svg>').format(
                    idx, rowlen, image_shape[0], 'http://www.w3.org/2000/svg',
                    idx, xcoord + (minx - 2), ycoord + (miny - 2), ''.join(svg_dirs), pa)
            else:
                svg = '<path id="superpixelp_{0:d}" d="M{1:d} {2:d}{3:s}z" {4:s} />'.format(
                    idx, xcoord + (minx - 2), ycoord + (miny - 2), ''.join(svg_dirs), pa)
            pix_shapes[idx] = svg
    if out_format in ['osvg', 'svg']:
        pix_shapes = ('<svg id="superpixels" width="{0:d}" height="{1:d}" ' +
            'xmlns="http://www.w3.org/2000/svg">\n    {2:s}\n</svg>').format(
            rowlen, image_shape[0], '\n    '.join(pix_shapes.values()))
    return pix_shapes

# write image
_write_imformats = {
    '.gif': 'gif',
    'gif': 'gif',
    '.jpeg': 'jpg',
    'jpeg': 'jpg',
    '.jpg': 'jpg',
    'jpg': 'jpg',
    '.png': 'png',
    'png': 'png',
    '.tif': 'tif',
    'tif': 'tif',
}
def write_image(
    image:numpy.ndarray,
    out:str,
    imformat:str = None,
    imshape:Tuple = None,
    jpg_quality:int = 90,
    ) -> Union[bool, bytes]:
    """
    Writes an image (data array) to file or buffer (return value)

    Parameters
    ----------
    image : numpy.ndarray
        Image data (HxWxplanes)
    out : str
        Output filename or 'buffer' (in that case returns the content)
    imformat : str
        Image format (only necessary if out == 'buffer')
    imshape : Tuple
        Image data shape (if given, will attempt to set prior to writing)
    
    Returns
    -------
    result : either bool or bytes
        For actual filenames returns True if write was successful, for
        out == 'buffer' returns the resulting byte stream
    """

    # IMPORTS DONE HERE TO SAVE TIME AT MODULE INIT
    from io import BytesIO
    from imageio import imwrite

    if imformat is None:
        if not '.' in out:
            raise ValueError('Cannot determine format.')
        out_parts = out.split('.')
        imformat = out_parts[-1].lower()
    else:
        imformat = imformat.lower()
    if not imformat in _write_imformats:
        raise ValueError('Format {0:s} not supported'.format(imformat))
    imformat = _write_imformats[imformat]
    oshape = image.shape
    if not imshape is None:
        try:
            image.shape = imshape
        except:
            raise
    with BytesIO() as buffer:
        try:
            if imformat == 'jpg':
                imwrite(buffer, image, imformat, quality=jpg_quality)
            else:
                imwrite(buffer, image, imformat)
        except:
            raise
        buffer_data = buffer.getvalue()
    image.shape = oshape
    if out == 'buffer':
        return buffer_data
    try:
        with open(out, 'wb') as outfile:
            if outfile.write(buffer_data) == len(buffer_data):
                return True
            else:
                return False
    except:
        raise
