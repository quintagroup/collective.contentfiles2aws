import os
import unittest2

from OFS.Image import File

from collective.contentfiles2aws.awsfile import AWSFile

from collective.contentfiles2aws.testing import \
        AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSFileFieldTestCase(unittest2.TestCase):
    """
    """
    layer = AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/image.gif' % dir_name, 'rb')

    def setUp(self):
        portal = self.layer['portal']
        fid = portal.invokeFactory('AWSFile', 'awsfile')
        self.awsfile = getattr(portal, fid)
        self.awsfile.update(file=self._get_image())

    def test_use_aws(self):
        self.assert_(not self.awsfile.schema['file'].use_aws(self.awsfile))

        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)

        self.assert_(self.awsfile.schema['file'].use_aws(self.awsfile))

    def test_migrate(self):
        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)

        self.assert_(self.awsfile.schema['file'].migrate(self.awsfile))

        fid = portal.invokeFactory('AWSFile', 'awsfile2')
        awsfile2 = getattr(portal, fid)
        awsfile2.update(file=self._get_image())

        self.assert_(not awsfile2.schema['file'].migrate(awsfile2))

    def test_do_migrate(self):
        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)
        self.assert_(self.awsfile.schema['file'].migrate(self.awsfile))

        self.awsfile.schema['file']._do_migrate(self.awsfile)
        self.assert_(not self.awsfile.schema['file'].migrate(self.awsfile))

    def test_get(self):
        localfile = self.awsfile.schema['file'].get(self.awsfile)

        self.assertEqual('File', localfile.meta_type)

        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)
        fid = portal.invokeFactory('AWSFile', 'awsfile2')
        awsfile2 = getattr(portal, fid)
        awsfile2.update(file=self._get_image())

        awsfile = awsfile2.schema['file'].get(awsfile2)
        self.assertEqual('AWS File', awsfile.meta_type)

    def test_set(self):
        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        sheet._updateProperty('USE_AWS', True)
        fid = portal.invokeFactory('AWSFile', 'awsfile2')
        awsfile2 = getattr(portal, fid)

        awsfile2.schema['file'].set(awsfile2, self._get_image())
        self.assert_(awsfile2.schema['file'].url(
            awsfile2).startswith('http://contentfiles.s3.amazonaws.com/'))

    def test_make_file(self):
        file = self.awsfile.schema['file']._make_file('testfile', factory=File)
        self.assertEqual(file.meta_type, File.meta_type)

        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('USE_AWS', True)
        awsfile = self.awsfile.schema['file']._make_file('testfile',
                                                      factory=AWSFile)
        self.assertEqual(awsfile.meta_type, AWSFile.meta_type)

    def test_url(self):
        portal = self.layer['portal']
        sheet = portal.portal_properties.contentfiles2aws
        sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        sheet._updateProperty('USE_AWS', True)
        fid = portal.invokeFactory('AWSFile', 'awsfile2')
        awsfile2 = getattr(portal, fid)
        awsfile2.update(file=self._get_image())

        self.assert_(awsfile2.schema['file'].url(
            awsfile2).startswith('http://contentfiles.s3.amazonaws.com/'))

def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSFileFieldTestCase))
    return suite
