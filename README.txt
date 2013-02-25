Introduction
============

This package brings to Plone the ability to store files and images on
amazon s3 service.

Overview
--------

The main idea is to move content images and files to amazon
CDN which serves content to end users with high availability and high
performance. The package contains two content types: AWSFile and AWSImage
which work similar to the default ones. The main difference is that they
store their content on amazon simple storage instead of Plone site.
Also package contains patch for default content types like Image, File and
News Item.


Compatibility
-------------

This add-on was tested for the Plone 3.3.5.

Requirements
------------

This package requires boto library (http://github.com/boto/boto)
that is compatible with python 2.4

This package was developed and tested with @1011 revision
of boto library. From manual checkout use this command::

  svn co http://boto.googlecode.com/svn/trunk@1011


Installation
------------

* to add the package to your Zope instance, please, follow the instructions
  found inside the
  ``docs/INSTALL.txt`` file

* then restart your Zope instance and install the
  ``collective.contentfiles2aws`` package from within the
  ``portal_quickinstaller`` tool.

After package is sucessfully installed it should be properly configured.
You need to create amazon account before you can configure package.

Amazon S3 bucket
----------------
Every file you upload to Amazon S3 is stored in a container called a bucket.
Before you start working with Amazon S3 you have to create at least one bucket.
The bucket namespace is shared by all users of the system; therefore each
bucket name should be unique. You can create up to 100 buckets per account.
Each bucket can contain an unlimited number of files. Buckets cannot be nested,
you can not create a bucket within a bucket. Bucket ownership is not
transferable; however, if a bucket is empty, you can delete it. After a bucket
is deleted, the name becomes available to reuse, however the name might not be
available for you to resuse for various reasons. For example, some other
account can create a bucket with that name. So if you want to use the same
bucket name, don't delete the bucket. Note that it might take some timeframe
before the name can be reused.
  There is no limit to the number of objects that can be stored in a bucket
and no variation in performance whether you use many buckets or just a few.
You can store all of your objects in a single bucket, or you can organize them
across several buckets.

Rules for Bucket Naming
-----------------------
In all regions except for the US Standard region a bucket name mustcomply
with the following rules. These result in a DNS compliant bucket name.
 * Bucket names must be at least 3 and no more than 63 characters long
 * Bucket name must be a series of one or more labels separated
 by a period (.), where each label:
 * Must start with a lowercase letter or a number
 * Must end with a lowercase letter or a number
 * Can contain lowercase letters, numbers and dashes
 * Bucket names must not be formatted as an IP address (e.g., 192.168.5.4)

 The following are examples of valid bucket names:
   *myawsbucket
   *my.aws.bucket
   *myawsbucket.1

These naming rules for US Standard region can result in a bucket name that
is not DNS-compliant. For example, MyAWSBucket, is a valid bucket name, with
uppercase letters in its name. If you try to access this bucket using a virtual
hosted-style request, http://MyAWSBucket.s3.amazonaws.com/yourobject,
the URL resolves to the bucket myawsbucket and not the bucket MyAWSBucket.
In response, Amazon S3 will return a bucket not found error.
To avoid this problem, we recommend as a best practice that you
always DNS-compliant bucket names regardless of the region in which you
create the bucket. For more information about virtual-hosted style access to
your buckets, see Virtual Hosting of Buckets.

Configuration
-------------
To configure package to work with you amazon account you need to accomplish
the following steps:
 * find 'portal_properties' tool in your site root and open it;
 * find 'contentfiles2aws' property scheet and click on it;
 * fill in your aws key id into AWS_KEY_ID field;
 * fill in your aws secret key into AWS_SEECRET_KEY field;
 * fill in created bucket name into AWS_BUCKET_NAME field;
 * optionally you can fill in AWS_FILENAME_PREFIX with the name of a folder
   in bucket. This folder will be used to store your files. Also you can
   provide slash separated path, for example: folder1/folder2/folder3
   Actually there are no folders in s3, only key/value pairs. The key can
   contain slashes ("/") and that will make it appear as a folder in management
   console, but programmatically it's not a folder it is a string value.
   Anyway if you prefer to use folder you can specify one in
   AWS_FILENAME_PREFIX field
 * turn on 'USE_AWS' checkbox on. This checkbox allows you to turn on or
   turn off amazon storage. If 'USE_AWS' checkbox is turned off that means
   that all newly created content types that use aws file or image fields will
   work like default ones and store their values in database. Objects that were
   created before you turned off 'USE_AWS' check box will work as usual. If you
   turn 'USE_AWS' checkbox on all newly created objects with aws file or image
   fields will store their values to amazon storage.


Custom content type
-------------------

If you want to have ability to store images or files to aws storage in your
custom content type you need to do the following steps:
  * use AWSImageField or AWSFileField instead default ImageField or File field
    in your content type schema.
  * use AWSImageWidget and AWSFieldWidget for AWSImageField and AWSFileField
    accordingly.
  * use AWSStorage instead AnnotationStorage for AWSImageField or AWSFileField.

Here is exmaple of simple aws image field::

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

In case you have a lot of images and files in your site and you want to
move them all to amazon storage there is simple migration procedure that you
can use. Migration script (zope 3 view) named 'migrate-content' can be called
on any context. If you call 'migrate-content' view you will see the list of
of content types that have at least one aws field (image or file) in their 
schema. (If your content types isn't in that list, it means that you do not
use aws fields in it or use default Image and File fields instead aws ones.)
Against of content types list you will see count of object for each content
type founded on this context. To migrate object for specific content type
you need to pass 'content_type' parameter for 'migrate-content' script.
For example if you want to migrate Image content type you need to specify it
like this:
     http://yourdomain/somefolder/migrate-content?content_type=Image
In case you want to migrate all objects for all content types that was founded
on current context you need to specify 'all' value for content_type parameter,
like this:
     http://yourdomain/somefolder/migrate-content?content_type=all
After script finish migration it will show list of migrated content types and
count of fields migrated for each content type.

Note: migration is time consuming procedure. It can take from a few minutes up
to several hours, it depends on amount of files and images in your database.
Be patient ... ;)





Security and Backup
------------------



Credits
=======

Companies
---------

|martinschoel|_

* `Martin Schoel Web Productions <http://www.martinschoel.com/>`_
* `Contact us <mailto:python@martinschoel.com>`_


Authors
-------

* Taras Melnychuk <melnychuktaras@gmail.com>


Contributors
------------

.. |martinschoel| image:: http://cache.martinschoel.com/img/logos/MS-Logo-white-200x100.png
.. _martinschoel: http://www.martinschoel.com/
