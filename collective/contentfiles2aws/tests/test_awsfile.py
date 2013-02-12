import os
import unittest2

from zope.component import getUtility

from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSFileTestCase(unittest2.TestCase):
    """ AWS File test case. """

    layer = AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)
        sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')

        id = portal.invokeFactory('AWSFile', 'awsfile')
        self.awsfile = getattr(portal, id)
        self.awsfile.update(file=self._get_image())
        self.aws_file = self.awsfile.getFile()

    def test_index_html(self):
        """ Tests index_html method."""
        request = self.layer['request']
        response = request.RESPONSE
        self.aws_file.index_html(request, response)
        self.assertEqual(self.aws_file.absolute_url(),
                         request.RESPONSE.getHeader('location'))

    def test_absolute_url(self):
        """ Test url creation."""
        self.assertEqual('http://contentfiles.s3.amazonaws.com/' +
                         self.aws_file.source_id, self.aws_file.absolute_url())

    def test_remove_source(self):
        """ Test remove_source method."""
        self.aws_file.remove_source()
        aws_utility = getUtility(IAWSFileClientUtility)
        as3client = aws_utility.getFileClient()
        self.assert_(not as3client.get(self.aws_file.source_id))


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSFileTestCase))
    return suite
