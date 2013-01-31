import os
import unittest2

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

    def test_do_migrate(self):
        self.conf_sheet._updateProperty('USE_AWS', True)
        image_field = self.awsimage.schema['image']
        self.assert_(image_field.migrate(self.awsimage))

        image_field._do_migrate(self.awsimage)
        self.assert_(not image_field.migrate(self.awsimage))

        for n, s in image_field.getAvailableSizes(self.awsimage).items():
            storage = image_field.getStorage(self.awsimage)
            scale = storage.get('image_' + n, self.awsimage)
            self.assertEqual('AWS Image', scale.meta_type)

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
            self.assertEqual('AWS Image', scale.meta_type)


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSImageFieldTestCase))
    return suite
