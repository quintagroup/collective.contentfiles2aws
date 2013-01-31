import unittest2

from zope.component import getUtility

from plone.app.testing import setRoles, TEST_USER_ID

from collective.contentfiles2aws.interfaces import IAWSUtility
from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSFileTestCase(unittest2.TestCase):
    """ AWS File test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def setUp(self):
        portal = self.layer['portal']
        # set test bucket name
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')

        factory_dispatcher = \
                portal.manage_addProduct['collective.contentfiles2aws']
        factory = getattr(factory_dispatcher, 'manage_addFile')
        factory('file', file='data', content_type='text/plain')
        self.aws_file = getattr(portal, 'file')

    def test_make_prefix(self):
        """ Tests generated prefix creation. """
        prefix = self.aws_file.make_prefix()
        # each method call should generate new hash
        self.assertNotEqual(prefix, self.aws_file.make_prefix())

    def test_NormalizedName(self):
        """ Test filename normalizer. """

        setattr(self.aws_file, 'filename',
                u'\u0456\u043c\u044f\u0444\u0430\u0439\u043b\u0443.txt')
        self.assertEqual('45643c44f44443043b443.txt',
                         self.aws_file.getNormalizedName())

    def test_sourceId(self):
        """ Tests source id generation."""

        self.assert_(self.aws_file.getSourceId().endswith('_file'))
        setattr(self.aws_file, 'filename', 'filename.txt')
        source_id = self.aws_file.getSourceId(fresh=True)
        self.assert_(source_id.endswith('_file_filename.txt'))

        # test uid part, for this we need to create new file in some folder
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        fid = portal.invokeFactory('Folder', 'test_folder')
        setRoles(portal, TEST_USER_ID, ['Member'])
        folder = getattr(portal, fid)

        factory_dispatcher = \
                folder.manage_addProduct['collective.contentfiles2aws']
        factory = getattr(factory_dispatcher, 'manage_addFile')
        factory('new_file', file='data', content_type='text/plain')
        awsfile = getattr(folder, 'new_file')
        self.assert_(awsfile.getSourceId().startswith(folder.UID()))

    def test_update_source(self):
        """ Test update_source method."""
        setattr(self.aws_file, 'filename', 'filename.txt')
        self.aws_file.update_source('new text', 'text/plain')

        self.assertEqual(self.aws_file.getSourceId(),
                         self.aws_file.uploaded_source_id)

        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assertEqual(as3client.get(self.aws_file.getSourceId()),
                         'new text')

    def test_update_data(self):
        """ Test update_data method."""
        setattr(self.aws_file, 'filename', 'filename.txt')
        self.aws_file.update_data('new text', content_type='text/plain')

        self.assertEqual(self.aws_file.getSourceId(),
                         self.aws_file.uploaded_source_id)

        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assertEqual(as3client.get(self.aws_file.getSourceId()),
                         'new text')

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
                self.aws_file.getSourceId(), self.aws_file.absolute_url())

    def test_remove_source(self):
        """ Test remove_source method."""
        self.aws_file.remove_source()
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        self.assert_(not as3client.get(self.aws_file.getSourceId()))


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSFileTestCase))
    return suite
