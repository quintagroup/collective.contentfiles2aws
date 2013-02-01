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


Compatibility
-------------

This add-on was tested for the Plone 3.3.5.

Requirements
------------

This package requires boto library (https://github.com/boto/boto)
that is compatible with python 2.4

This package was developed and tested with @1011 revision
of boto library (http://boto.googlecode.com/svn/trunk@1011)


Installation
------------

* to add the package to your Zope instance, please, follow the instructions
  found inside the
  ``docs/INSTALL.txt`` file

* then restart your Zope instance and install the
  ``collective.contentfiles2aws`` package from within the
  ``portal_quickinstaller`` tool.


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
