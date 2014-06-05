import os
import unittest2

from zope.component import getMultiAdapter

from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError

from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING

from collective.contentfiles2aws.tests.test_catalog import createScales


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

    def test_aws_image_url(self):
        """ This specific test was made to cover issue #1444.

        This test covers fix for case when not all image scales was
        created as amazon images due to some issues with network or
        access to amazon service.
        """

        self.patch_scale_creation()
        self.create_test_image()

        portal = self.layer['portal']
        request = self.layer['request']

        obj_brain = portal.portal_catalog(id='aws_image')[0]
        aws_image_url = getMultiAdapter((portal, request),
                                        name = 'aws_image_url')
        self.assertEqual(aws_image_url(obj_brain, scale='tile'),
                         'http://nohost/plone/aws_image/image_tile')


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSIndexersTestCase))
    return suite
