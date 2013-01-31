import os
import unittest2

from zope.component import getUtility

from plone.app.testing import setRoles, TEST_USER_ID

from collective.contentfiles2aws.interfaces import IAWSUtility
from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSImageTestCase(unittest2.TestCase):
    """ AWS File test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        portal = self.layer['portal']
        # set test bucket name
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')

        factory_dispatcher = \
                portal.manage_addProduct['collective.contentfiles2aws']
        factory = getattr(factory_dispatcher, 'manage_addImage')
        factory('image', file=self._get_image(), content_type='image/gif')
        self.aws_image = getattr(portal, 'image')

    def test_make_prefix(self):
        """ Tests generated prefix creation. """
        prefix = self.aws_image.make_prefix()
        # each method call should generate new hash
        self.assertNotEqual(prefix, self.aws_image.make_prefix())

    def test_NormalizedName(self):
        """ Test filename normalizer. """

        setattr(self.aws_image, 'filename',
                u'\u0456\u043c\u044f\u0444\u0430\u0439\u043b\u0443.txt')
        self.assertEqual('45643c44f44443043b443.txt',
                         self.aws_image.getNormalizedName())

    def test_sourceId(self):
        """ Tests source id generation."""

        self.assert_(self.aws_image.getSourceId().endswith('_image'))
        setattr(self.aws_image, 'filename', 'filename.gif')
        source_id = self.aws_image.getSourceId(fresh=True)
        self.assert_(source_id.endswith('_image_filename.gif'))

        # test uid part, for this we need to create new file in some folder
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        fid = portal.invokeFactory('Folder', 'test_folder')
        setRoles(portal, TEST_USER_ID, ['Member'])
        folder = getattr(portal, fid)

        factory_dispatcher = \
                folder.manage_addProduct['collective.contentfiles2aws']
        factory = getattr(factory_dispatcher, 'manage_addFile')
        factory('new_file', file='data', content_type='image/gif')
        awsfile = getattr(folder, 'new_file')
        self.assert_(awsfile.getSourceId().startswith(folder.UID()))

    def test_update_source(self):
        """ Test update_source method."""
        setattr(self.aws_image, 'filename', 'filename.gif')
        self.aws_image.update_source('new text', 'image/gif')

        self.assertEqual(self.aws_image.getSourceId(),
                         self.aws_image.uploaded_source_id)

        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assertEqual(as3client.get(self.aws_image.getSourceId()),
                         'new text')

    def test_update_data(self):
        """ Test update_data method."""
        setattr(self.aws_image, 'filename', 'filename.gif')
        self.aws_image.update_data('new text', content_type='image/gif')

        self.assertEqual(self.aws_image.getSourceId(),
                         self.aws_image.uploaded_source_id)

        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assertEqual(as3client.get(self.aws_image.getSourceId()),
                         'new text')

    def test_index_html(self):
        """ Tests index_html method."""
        request = self.layer['request']
        response = request.RESPONSE
        self.aws_image.index_html(request, response)
        self.assertEqual(self.aws_image.absolute_url(),
                         request.RESPONSE.getHeader('location'))

    def test_absolute_url(self):
        """ Test url creation."""
        self.assertEqual('http://contentfiles.s3.amazonaws.com/' +
                self.aws_image.getSourceId(), self.aws_image.absolute_url())

    def test_remove_source(self):
        """ Test remove_source method."""
        self.aws_image.remove_source()
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assert_(not as3client.get(self.aws_image.getSourceId()))

    def test_tag(self):
        self.assert_('http://contentfiles.s3.amazonaws.com/' in \
                     self.aws_image.tag())


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSImageTestCase))
    return suite
