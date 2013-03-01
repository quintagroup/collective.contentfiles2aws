Introduction
============

With the collective.contentfiles2aws package, you can store Plone files
and images on amazon s3 service.


Overview
--------

The main purpose of the package to move content images and files to amazon
CDN, that allows to serve content to end users with high performance and
high availability. The package contains two content types: AWSFile and AWSImage
which work similar to the default Plone ones. The main difference is that they
store their content on amazon simple storage instead of a Plone site.
Also, the package contains a patch for default content types like Image, File,
and News Item.


Compatibility
-------------

The package was tested on Plone 3.3.5.


Requirements
------------

The package requires boto library (http://github.com/boto/boto)
that is compatible with python 2.4.

This package was developed and tested with @1011 revision
of boto library. For manual checkout, use this command::

 svn co http://boto.googlecode.com/svn/trunk@1011


Installation
------------

To add the package to your Zope instance, do the following:

1. Follow the instructions provided in the ``docs/INSTALL.txt`` file.
2. Restart your Zope instance.
3. Install the ``collective.contentfiles2aws`` package with Quickinstaller in
   Plone (Site Setup > Add/Remove Products).

After the package is installed, it should be configured properly. For this,
you need to have an amazon account.


Amazon S3 bucket
----------------

Every file that you upload to Amazon S3 is stored in a container called
a bucket. Before you start working with Amazon S3, you must create at least
one bucket. The bucket namespace is shared by all users of the system;
therefore, name of each bucket should be unique. You can create up to 100
buckets per account. Each bucket can contain an unlimited number of files.
Buckets cannot be nested: you cannot create a bucket within a bucket.
Bucket ownership is not transferable; however, if a bucket is empty,
you can delete it. After a bucket is deleted, the name becomes available for
reuse. However, the name might be unavailable for reuse because of various
reasons, for example, a bucket with the same name can be created by another
account. So, if you want to use the same bucket name, don't delete the bucket.
Note that it might take some time before the name can be reused.

There is no limit to the number of objects that can be stored in a bucket.
Performance is not impacted by the number of buckets that you use.
You can store all of your objects in a single bucket, or you can organize them
across several buckets.


Rules for Bucket Naming
-----------------------

In all regions except for the US Standard region, a bucket name must comply
with the following rules (as a result of a DNS compliant bucket name):
* Bucket name must be at least 3 and no more than 63 characters long
* Bucket name must be a series of one or more labels separated
by a period (.), where each label:
    * Must start with a lowercase letter or a number
    * Must end with a lowercase letter or a number
    * Can contain lowercase letters, numbers, and dashes
    * Bucket names must not be formatted as IP addresses (e.g., 192.168.5.4)

The following are examples of valid bucket names:
  *myawsbucket
  *my.aws.bucket
  *myawsbucket.1

These naming rules for US Standard region can result in a bucket name that
is not DNS compliant. For example, MyAWSBucket – is a valid bucket name with
uppercase letters in its name. If you try to access this bucket using a virtual
hosted-style request, http://MyAWSBucket.s3.amazonaws.com/yourobject,
the URL resolves to the bucket myawsbucket and not the bucket MyAWSBucket.
In response, Amazon S3 will return a not found error.
To avoid this problem, we recommend that you always use DNS-compliant bucket
names regardless of the region in which you create the bucket.


Configuration
-------------

To configure the collective.contentfiles2aws package to work with you amazon
account, you need to accomplish the following steps:

1. In your site root, open the 'portal_properties' tool
2. Find 'contentfiles2aws' property sheet and click it
3. In the AWS_KEY_ID field, enter your aws key id
4. In the AWS_SEECRET_KEY field, enter your aws secret key
5. In the AWS_BUCKET_NAME field, enter the name of the created bucket
6. (optional) In the AWS_FILENAME_PREFIX field, enter the name of a folder
   in bucket. This folder will be used to store your files. Also, you can
   provide slash separated path, for example: folder1/folder2/folder3.
   Actually, there are no folders in Amazon S3, only key/value pairs. The key
   can contain slashes ("/") and that will make it appear as a folder in
   management console, but programmatically it's not a folder, it is a string
   value.  Anyway, if you prefer using folder, you can specify one in the
   AWS_FILENAME_PREFIX field.
7. Select the USE_AWS check box.
   This check box allows you to turn on or turn off amazon storage.
   If 'USE_AWS' check box is not selected, that means that all newly created
   content types that use aws file or image fields will work like default ones,
   and will store their values in the database. Objects that were created
   before you remove selection from  the USE_AWS check box will work as usual.
   If you select the USE_AWS check box, all newly created objects with aws file
   or image fields will store their values to amazon storage.


Custom content type
-------------------

If you want to store images or files to aws storage in your custom content
type, you need to do the following steps:

 1. Use AWSImageField or AWSFileField instead default ImageField or File field
    in your content type schema.
 2. Use AWSImageWidget and AWSFieldWidget for AWSImageField and AWSFileField
    accordingly.
 3. Use AWSStorage instead of AnnotationStorage for AWSImageField or
    AWSFileField.

Here is example of simple aws image field::

    `AWSImageField`('image',
                 required=True,
                 primary=True,
                 languageIndependent=True,
                 storage = `AWSStorage()`,
                 pil_quality = zconf.pil_config.quality,
                 pil_resize_algo = zconf.pil_config.resize_algo,
                 max_size = zconf.ATImage.max_image_dimension,
                 sizes= {'large'   : (768, 768),
                         'preview' : (400, 400),
                         'mini'    : (200, 200),
                         'thumb'   : (128, 128),
                         'tile'    :  (64, 64),
                         'icon'    :  (32, 32),
                         'listing' :  (16, 16),
                        },
                 validators = (('isNonEmptyFile', V_REQUIRED),
                               ('checkImageMaxSize', V_REQUIRED)),
                 widget = `AWSImageWidget`(
                          description = '',
                          label= _(u'label_image', default=u'Image'),
                          show_content_type = False,)),


Migration
---------

If you have a lot of images and files on your site, and you want to
move them all to amazon storage, there is a simple migration procedure that you
can follow. Migration script (zope 3 view) named 'migrate-content' can be
called on any context. If you call 'migrate-content' view, you will see a list
of content types that have at least one aws field (image or file) in their
schema. (If your content type is not in that list, it means that you do not
use aws fields in it, or you use default Image and File fields instead of aws
ones.) Next to the content types list, you will see the number of objects for
each content type found on this context. To migrate object for specific content
type, you need to pass 'content_type' parameter for 'migrate-content' script.

For example, if you want to migrate Image content type, you need to specify it
like this:
    http://yourdomain/somefolder/migrate-content?content_type=Image

If you want to migrate all objects for all content types that were found
on the current context, you need to specify 'all' value for content_type
parameter, like this:
    http://yourdomain/somefolder/migrate-content?content_type=all

After a script finishes the migration, it will show a list of migrated content
types and number of migrated fields for each content type.

Note: Migration is a time consuming procedure. It can take from a few minutes
up to several hours, depending on the amount of files and images in your
database.


Safety
-------

After you installed the package, configured it, and turned AWS storage on,
all files and images will be stored in amazon s3 storage. It means that during
object creation, file data will be send to a remote server. In case remote
server is inaccessible for some reasons (bad configuration or issues on server
side), your data will not be lost, it will be saved in site database,
as if you were using a default Image or File instead of AWS one. After all
issues were resolved, all AWS files and images that were created when amazon
was not accessible, can easily be migrated to amazon. To migrate such objects,
you need to click the edit action, and then, on the edit form, under the image
or file you will see an info box saying that this image or file is currently
saved in a database. After you click the Save button, regardless if you make
any changes or not, the system will try to migrate image or file to amazon.
If migration is successful, info box will disappear from the edit form.


Url generation
--------------

AWSImagField and AWSFileField have widgets that generate proper URL
to the image or file. Depending on the place where the data is stored, URL will
point to amazon or your site. If you decide not to use the widget, you
can use 'aws_image_url' and 'aws_file_url' helper views for image and file
URL generation accordingly. Here is an example of file URL helper view usage::

    >>> from zope.component import getMultiAdapter
    >>> aws_file_url = \
    ...    getMultiAdapter((context, request), name=u'aws_file_url')
    >>> aws_file_url(instance, name='fieldname', brain=False)

where:
 * instance - is content object or brain;
 * name     - field name;
 * brain    - boolean flag that need to be set to False if instance is object
              not brain. (True - by default)

For image URL helper view usage::

    >>> from zope.component import getMultiAdapter
    >>> aws_image_url = \
    ...    getMultiAdapter((context, request), name=u'aws_image_url')
    >>> aws_image_url(instance, name='fieldname',
    ...               scale='scale_name', brain=False)

where:
 * instance - is content object or brain;
 * name - field name;
 * scale - image scale (None - by default);
 * brain - boolean flag that need to be set to False if instance is object
             not brain. (True - by default);


Credits
=======

Companies
---------

|martinschoel|_

* `Martin Schoel Web Productions <http://www.martinschoel.com/>`_
* `Contact us <mailto:python@martinschoel.com>`_


Author
-------

* Taras Melnychuk <melnychuktaras@gmail.com>


Contributors
------------

.. |martinschoel| image:: http://cache.martinschoel.com/img/logos/MS-Logo-white-200x100.png
.. _martinschoel: http://www.martinschoel.com/
