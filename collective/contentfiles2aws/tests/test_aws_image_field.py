import os
import unittest2

from OFS.Image import Image

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.testing import \
        AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSImageFieldTestCase(unittest2.TestCase):
    """
    """
    layer = AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        self.portal = self.layer['portal']
        fid = self.portal.invokeFactory('AWSImage', 'awsimage')
        self.awsimage = getattr(self.portal, fid)
        self.awsimage.update(image=self._get_image())
        self.conf_sheet=self.portal.portal_properties.contentfiles2aws

    def test_wrapValue(self):
        field = self.awsimage.schema['image']
        image = field._wrapValue(self.awsimage, '')
        self.assert_(isinstance(image, Image))

        self.assert_(isinstance(field._wrapValue(self.awsimage, image), Image))
        awsfile = AWSFile('awsfile')
        self.assert_(isinstance(field._wrapValue(self.awsimage, awsfile),
                                AWSFile))

    def test_get(self):
        field = self.awsimage.schema['image']
        image = field.get(self.awsimage)
        self.assert_(isinstance(image, Image))

        self.conf_sheet._updateProperty('USE_AWS', True)
        self.awsimage.REQUEST['image_migrate'] = True
        image = field.get(self.awsimage)
        self.assert_(isinstance(image, AWSFile))
        for n in field.getAvailableSizes(self.awsimage).keys():
            scale = field.getScale(self.awsimage, scale=n)
            self.assert_(isinstance(scale, AWSFile))

    def test_set(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)
        fid = self.portal.invokeFactory('AWSImage', 'awsimage2')
        awsimage2 = getattr(self.portal, fid)

        awsimage2.schema['image'].set(awsimage2, self._get_image())
        self.assert_(awsimage2.schema['image'].url(
            awsimage2).startswith('http://contentfiles.s3.amazonaws.com/'))

        image_field = awsimage2.schema['image']
        for n, s in image_field.getAvailableSizes(awsimage2).items():
            storage = image_field.getStorage(awsimage2)
            scale = storage.get('image_' + n, awsimage2)
            self.assertEqual('AWS File', scale.meta_type)

    def test_createScales(self):
        self.conf_sheet._updateProperty('USE_AWS', True)
        field = self.awsimage.schema['image']
        field.sizes['new_scale'] = (100, 100)
        field.createScales(self.awsimage)
        new_scale = field.getScale(self.awsimage, scale='new_scale')
        self.assert_(isinstance(new_scale, AWSFile))

    def test_tag(self):
        self.conf_sheet._updateProperty('USE_AWS', True)
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        field = self.awsimage.schema['image']

        self.assertEqual(field.tag(self.awsimage, scale='thumb'),
                        ('<img src="http://nohost/plone/awsimage/image_thumb"'
                         ' alt="" title="" height="16" width="16" />'))
        self.awsimage.REQUEST['image_migrate'] = True
        field.get(self.awsimage)
        tag = field.tag(self.awsimage, scale='thumb')
        self.assert_(
            tag.startswith('<img src="http://contentfiles.s3.amazonaws.com/'))
        self.assert_(tag.endswith(('image_thumb_image.gif" alt="" title=""'
                                   ' height="" width="" />')))


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSImageFieldTestCase))
    return suite
