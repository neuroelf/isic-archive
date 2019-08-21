# isic-archive (ISIC Archive access python module)
The [ISIC Archive](https://www.isic-archive.com/) is an online repository and
archive published and maintained by the International Skin Imaging
Collaboration. Next to the human-readable and browsable website, it also
provides a publicly available [API](https://isic-archive.com/api/v1), which
offers several functions (called endpoints) for interacting with the data
programmatically.

The present python package is an attempt at bundling the more frequently used
functionality into a single module, thus reducing the need to re-write certain
code for a diverse set of projects.

## First steps
To start with, please import the ```IsicApi``` class from the ```isicarchive```
module and create an instance of the class:

~~~~
from isicarchive import IsicApi
api = IsicApi()
~~~~

### Data availability
All general features are available without logging into the API. However,
since many datasets (and with them their images) as well as studies are not
marked as being "publicly available", the number of items returned by
many functions (endpoints) differ based on whether you have successfully
authenticated with the API. If you do not plan to register a username, you
can skip the next section, and either set the ```username``` parameter to
```None``` or skip it altogether in the call to ```IsicApi```.

### Logging into the ISIC Archive
For instance, some annotations created by study participants, or retrieving
certain images that are not marked for public access requires that you are
logged into the archive/API. This can be achieved by instantiating the
```IsicApi``` object with a valid username (and password):

~~~~
# set username
username = 'address@provider.com'

# create API object
api = IsicApi(username)

# or, if you can securely store a password as well
api = IsicApi(username, password)
~~~~

**Please do *not* enter the password in clear text into your source code**. If
you provide only the username, the password will be requested from either the
console or, if used in a Jupyter notebook, below the active cell using the
```getpass``` library.

### Local cache folder
Since a lot of the data that can be retrieved from the archive (API) is
relatively static--that is, it will not change between uses of the API--you
can keep a locally cached copy, which will speed up processing of data on
the next call you use the same image or annotation, for instance. To do so,
please add the ```cache_folder``` parameter to the call, like so:

~~~~
# For Linux/Mac
cache_folder = '/some/local/folder'
# For Windows
cache_folder = 'C:\\Users\\username\\some\\local\\folder' # use double \\ !

# Create object
api = IsicApi(cache_folder=cache_folder)
# or
api = IsicApi(username, cache_folder=cache_folder)
# or
api = IsicApi(username, password, cache_folder=cache_folder)
~~~~

Relatively large and complex data (annotations, images, etc.) will have a
stored local copy, which means that they can be retrieved later from the
cache, instead of having to request them again from the web-based API.

Within the cache folder the ```IsicApi``` object will, on first use,
create 16 subfolders, named ```0``` through ```9```, and ```a``` through
```f``` (the 16 hexadecimal digits), to avoid downloading too many files
into a single folder, which would slow down the operation later on. For each
file, the sub-folder is determined by the last hexadecimal digit of the
unique object ID (explained below).

Images are stored with a filename pattern of ```image_[objectId]_[name].ext```
whereas ```objectId``` is the unique ID for this image within the archive,
```name``` is the filename (typically ```ISIC_xxxxxxx```), and ```.ext``` is
the extension as provided by the Content-Type header of the downloaded image.

Superpixel images (also explained below) are stored with the filename pattern
of ```spimg_[objectId].png``` using the associated image's object ID! In
addition, a derived superpixel index array is stored with a filename pattern
of ```spidx_[objectID].npz``` (using ```numpy.savez```).

### Caching information about all images
Since the archive contains several thousand images, it can often be helpful
to be able to search for specific images. To do so locally, you can download
the details about all images available in the archive (if you're) calling
the ```IsicApi``` object with the cache_folder parameter) like so:

~~~~
# Populate image cache
api.cache_images()

# display information about image ISIC_000000 (by its ID) from the cache
image_info = api.image_cache[api.images['ISIC_0000000']]
print(image_info)
~~~~

When called for the first time, building the cache may take several minutes.
Once the information is downloaded, however, only a single call will be made to
the web-based API to confirm that, indeed, no new images are available. **For
this to work, however, it is important that you do not use the same
cache folder for sessions where you are either logged in (authenticated)
versus not!**

## Some more details on the web-based API
Any interaction with the web-based API is performed by the ```IsicApi```
object through the HTTPS protocol, using the
[requests](https://2.python-requests.org/en/master/) package methods. As part
of the requests made, the endpoint (function and type of element being
interacted with) is specified, and one or several parameters can be set,
which are appended to the URL. For instance, retrieving information about
one specific image would be achieved by accessing the following URL:

```https://isic-archive.com/api/v1/image/5436e3abbae478396759f0cf```

This last portion of the URL that appears after the ```image/``` part is
called the (object) id, and is a system-wide unique value that identifies
each element to ensure that one interacts only with the intended target.

The output of the URL above is (slightly truncated for brevity):

~~~~
{
  "_id": "5436e3abbae478396759f0cf",
  "_modelType": "image",
  "created": "2014-10-09T19:36:11.989000+00:00",
  "creator": {
    "_id": "5450e996bae47865794e4d0d",
    "name": "User 6VSN"
  },
  "dataset": {
    "_accessLevel": 0,
    "_id": "5a2ecc5e1165975c945942a2",
    "description": "Moles and melanomas.",
    "license": "CC-0",
    "name": "UDA-1",
    "updated": "2014-11-10T02:39:56.492000+00:00"
  },
  "meta": {
    "acquisition": {
      "image_type": "dermoscopic",
      "pixelsX": 1022,
      "pixelsY": 767
    },
    "clinical": {
      "age_approx": 55,
      "anatom_site_general": "anterior torso",
      "benign_malignant": "benign",
      "diagnosis": "nevus",
      "diagnosis_confirm_type": null,
      "melanocytic": true,
      "sex": "female"
    }
  },
  "name": "ISIC_0000000",
  "updated": "2015-02-23T02:48:17.495000+00:00"
}
~~~~

Pretty much all elements available through the API are returned in the form of
their [JSON](https://en.wikipedia.org/wiki/JSON) representation (notation). And
lists of elements are returned as arrays. The exception are binary blobs (such
as image data, superpixel image data, and mask images).

Within the ISIC archive (and thus for the API), the following elements are
recognized:

- images (having both a JSON and several associated binary blob elements)
- segmentations (also having a JSON and a binary mask image component)
- datasets (collection of images)
- studies (selection of images from multiple datasets, together with questions and features to be annotated by users)
- annotations (responses to questions and image-based per-feature annotation as a selection of "superpixels")
- users (information about each registered user)
- tasks (information about tasks assigned to the logged in user)

### Image superpixels
As part of the image processing capabilities of the ISIC Archive itself, each
image that is uploaded will be automatically compartmentalized into about 1,000
patches of roughly equal size. E.g. for an image with a 4-by-3 aspect ratio,
there would be roughly 36 times 27 superpixels. The superpixel information is
stored in a specifically RGB-encoded image, such that for each superpixel the
patch has a (for the computer uniquely represented) RGB color code:

![ISIC_0000000 image superpixels](data/ISIC_0000000_superpixels_demo.png?raw=true "Superpixel demonstration")

The ```IsicApi.image.Image``` class contains functions to decode and map this
image first into an index array, and then into a mapping array:

~~~~
from isicarchive import IsicApi

# load superpixel image for first image
api = IsicApi()
image = api.image('ISIC_0000000')
image.load_superpixels()
superpixel_index_image = image.superpixels['idx']
image.map_superpixels()
superpixel_mapping = image.superpixels['map']
~~~~

### Retrieving information about a study
~~~~
study = api.study(study_name)
~~~~

This will make a call to the ISIC archive web API, and retrieve the
information about the study named in ```study_name```. If the study is not
found, an exception is raised!

The returned value, ```study``` is an object of type ```isicarchive.Study```,
and this provides some additional methods.

In addition to the information regularly provided by the ISIC Archive API,
the IsicApi object's implementation will also attempt to already download
information about annotations.

### Retrieving information about a dataset
~~~~
dataset = api.dataset(dataset_name)
~~~~

Similarly to a study, this will create an object of type
```isicarchive.Dataset```, which allows additional methods to be called.

In addition to the information regularly provided by the ISIC Archive API,
the IsicApi object's implementation will also attempt to already download
information about the access list, metadata, and images up for review.

### Retrieving images
~~~~
# Load the first image of the loaded study
image = api.image(study.images[0])
~~~~

This will, initially, only load the information about the image. If you would
like to make the binary data available, please use the following methods:

~~~~
# Load image data
image.load_data()

# Load superpixel image data
image.load_superpixels()

# Parse superpixels into a python dict (map) to pixel indices
image.map_superpixels()
~~~~

The mapping of an image takes a few seconds, but storing the map in a
different format would be relatively wasteful, and so this seems preferable.
