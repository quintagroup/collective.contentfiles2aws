import os
import unittest2

from Products.CMFCore.utils import getToolByName

from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSImageTestCase(unittest2.TestCase):
    """ AWSFile test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        self.portal = self.layer['portal']
        self.conf_sheet=self.portal.portal_properties.contentfiles2aws

    def test_AWSImageFTI(self):
        # test some basic fti properties.
        typestool = getToolByName(self.layer['portal'], 'portal_types')
        info = typestool._getOb('AWSImage')

        title = info.getProperty('title')
        self.assertEqual('AWSImage', title)

        meta_type = info.getProperty('content_meta_type')
        self.assertEqual('AWSImage', meta_type)

        global_allow = info.getProperty('global_allow')
        self.assert_(global_allow)

        view_methods = info.getProperty('view_methods')
        self.assert_('image_view' in view_methods)

    def test_AWSImageCreation(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)

        fid = self.portal.invokeFactory('AWSImage', 'aws_image')
        aws_image = getattr(self.portal, fid)
        aws_image.update(image=self._get_image())
        self.assertEqual(aws_image.portal_type, 'AWSImage')

        image_field = aws_image.schema['image']
        self.assert_('http://contentfiles.s3.amazonaws.com/' in \
                image_field.tag(aws_image))


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSImageTestCase))
    return suite
