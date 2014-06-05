import os
import unittest2

from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError

from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING

_marker = []

try:
    import PIL.Image
except ImportError:
    # no PIL, no scaled versions!
    log("Warning: no Python Imaging Libraries (PIL) found."+\
        "Archetypes based ImageField's don't scale if neccessary.")
    HAS_PIL=False
    PIL_ALGO = None
else:
    HAS_PIL=True
    PIL_ALGO = PIL.Image.ANTIALIAS

def createScales(self, instance, value=_marker):
    """creates the scales and save them
    """
    #import pdb; pdb.set_trace()
    sizes = self.getAvailableSizes(instance)
    if not HAS_PIL or not sizes:
        return
    # get data from the original size if value is None
    if value is _marker:
        img = self.getRaw(instance)
        if not img:
            return
        data = str(img.data)
    else:
        data = value

    # empty string - stop rescaling because PIL fails on an empty string
    if not data:
        return

    filename = self.getFilename(instance)

    for n, size in sizes.items():
        if size == (0,0):
            continue
        w, h = size
        id = self.getName() + "_" + n
        __traceback_info__ = (self, instance, id, w, h)
        try:
            imgdata, format = self.scale(data, w, h)
        except (ConflictError, KeyboardInterrupt):
            raise
        except:
            if not self.swallowResizeExceptions:
                raise
            else:
                log_exc()
                # scaling failed, don't create a scaled version
                continue

        mimetype = 'image/%s' % format.lower()
        if n == 'tile':
            pp = getToolByName(instance, 'portal_properties')
            pp.contentfiles2aws._updateProperty('USE_AWS', False)
        image = self._make_image(id, title=self.getName(), file=imgdata,
                                 content_type=mimetype, instance=instance)
        # nice filename: filename_sizename.ext
        #fname = "%s_%s%s" % (filename, n, ext)
        #image.filename = fname
        image.filename = filename
        try:
            delattr(image, 'title')
        except (KeyError, AttributeError):
            pass
        # manually use storage
        self.getStorage(instance).set(id, instance, image,
                                      mimetype=mimetype, filename=filename)
        if n == 'tile':
            pp = getToolByName(instance, 'portal_properties')
            pp.contentfiles2aws._updateProperty('USE_AWS', True)

class AWSIndexersTestCase(unittest2.TestCase):
    """ AWSINdexers test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def patch_scale_creation(self):
        from Products.Archetypes.Field import ImageField
        ImageField.createScales= createScales

    def create_test_image(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)

        fid = self.portal.invokeFactory('AWSImage', 'aws_image')
        aws_image = getattr(self.portal, fid)
        aws_image.update(image=self._get_image())

    def setUp(self):
        self.portal = self.layer['portal']
        self.conf_sheet=self.portal.portal_properties.contentfiles2aws

    def test_aws_sources(self):
        """ This specific test was made to cover issue #1444.

        This test covers fix for case when not all image scales was
        created as amazon images due to some issues with network or
        access to amazon service.
        """

        self.patch_scale_creation()
        self.create_test_image()

        obj = getattr(self.portal, 'aws_image')

        from collective.contentfiles2aws.catalog import aws_sources
        indexer = aws_sources(obj)
        self.assert_('image_tile' not in indexer())


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSIndexersTestCase))
    return suite
