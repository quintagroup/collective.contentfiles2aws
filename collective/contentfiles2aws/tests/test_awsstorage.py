import os
import unittest2

from OFS.Image import File
from zope.component import getUtility

from plone.app.testing import setRoles, TEST_USER_ID

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSStorageTestCase(unittest2.TestCase):
    """ AWS File test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        self.portal = self.layer['portal']
        # set test bucket name
        self.sheet = self.portal.portal_properties.contentfiles2aws
        self.sheet._updateProperty('USE_AWS', True)
        self.sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')

        id = self.portal.invokeFactory('AWSFile', 'awsfile')
        self.awsfile = getattr(self.portal, id)
        self.awsfile.update(file=self._get_image())
        self.storage = self.awsfile.schema['file'].storage
        self.aws_file = self.awsfile.getFile()

    def test_make_prefix(self):
        """ Tests generated prefix creation. """
        prefix = self.storage.make_prefix()
        # each method call should generate new hash
        self.assertNotEqual(prefix, self.storage.make_prefix())

    def test_NormalizedName(self):
        """ Test filename normalizer. """

        filename = u'\u0456\u043c\u044f\u0444\u0430\u0439\u043b\u0443.txt'
        self.assertEqual('45643c44f44443043b443.txt',
                         self.storage.getNormalizedName(filename))

    def test_sourceId(self):
        """ Tests source id generation."""

        source_id = self.storage.getSourceId('file',
                                             'filename.gif',
                                             self.awsfile)
        self.assert_(source_id.startswith(self.aws_file.UID()))
        self.assert_(source_id.endswith('_file_filename.gif'))

    def test_update_source(self):
        """ Test update_source method."""
        self.storage.update_source(self.aws_file,
                                   'new text',
                                   self.awsfile,
                                   'newfilename.gif',
                                   'image/gif')

        aws_utility = getUtility(IAWSFileClientUtility)
        as3client = aws_utility.getFileClient()
        self.assertEqual(as3client.get(self.aws_file.source_id), 'new text')
        self.assert_(self.aws_file.filename, 'newfilename.gif')
        self.assert_(self.aws_file.content_type, 'image/gif')

    def test_do_migrate(self):
        self.sheet._updateProperty('USE_AWS', False)

        id = self.portal.invokeFactory('AWSFile', 'file')
        file_ = getattr(self.portal, id)
        file_.update(file=self._get_image())
        storage = file_.schema['file'].storage
        file__ = file_.getFile()
        self.assert_(isinstance(storage._do_migrate(file__, file_), AWSFile))

    def test_get(self):
        self.assertEqual(self.aws_file, self.storage.get('file', self.awsfile))

        self.sheet._updateProperty('USE_AWS', False)
        id = self.portal.invokeFactory('AWSFile', 'file')
        file_ = getattr(self.portal, id)
        file_.update(file=self._get_image())
        storage = file_.schema['file'].storage
        file__ = file_.getFile()

        self.assert_(isinstance(file__, File))

        self.sheet._updateProperty('USE_AWS', True)
        file_.REQUEST['file_migrate'] = True
        self.assert_(isinstance(storage.get('file', file_), AWSFile))

    def test_set(self):
        self.sheet._updateProperty('USE_AWS', False)
        id = self.portal.invokeFactory('AWSFile', 'file')
        file_ = getattr(self.portal, id)
        storage = file_.schema['file'].storage

        ofsfile = File(id, '', self._get_image(), content_type='image/jpeg')
        storage.set('file', file_, ofsfile)
        self.assert_(storage.get('file', file_), File)

        self.sheet._updateProperty('USE_AWS', True)
        self.assert_(storage.get('file', file_), AWSFile)

    def test_unset(self):
        id = self.portal.invokeFactory('AWSFile', 'file')
        file_ = getattr(self.portal, id)
        storage = file_.schema['file'].storage

        ofsfile = File(id, '', self._get_image(), content_type='image/jpeg')
        setattr(ofsfile, 'filename', 'image.jpg')
        storage.set('file', file_, ofsfile)
        self.assert_(storage.get('file', file_), AWSFile)

        storage.unset('file', file_)
        self.assertRaises(AttributeError, storage.get, 'file', file_)

def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSStorageTestCase))
    return suite
