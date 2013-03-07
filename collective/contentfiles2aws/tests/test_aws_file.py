import os
import unittest2

from OFS.Image import File
from Products.CMFCore.utils import getToolByName

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.testing import \
    AWS_CONTENT_FILES_INTEGRATION_TESTING


class AWSFileTestCase(unittest2.TestCase):
    """ AWSFile test case. """

    layer =  AWS_CONTENT_FILES_INTEGRATION_TESTING

    def _get_image(self, filename='image.gif'):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        return open('%s/data/%s' % (dir_name, filename), 'rb')

    def setUp(self):
        self.portal = self.layer['portal']
        self.conf_sheet=self.portal.portal_properties.contentfiles2aws

    def test_AWSFileFTI(self):
        # test some basic fti properties.
        typestool = getToolByName(self.portal, 'portal_types')
        info = typestool._getOb('AWSFile')

        title = info.getProperty('title')
        self.assertEqual('AWSFile', title)

        meta_type = info.getProperty('content_meta_type')
        self.assertEqual('AWSFile', meta_type)

        global_allow = info.getProperty('global_allow')
        self.assert_(global_allow)

        view_methods = info.getProperty('view_methods')
        self.assert_('file_view' in view_methods)

    def test_AWSFileCreation(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)

        fid = self.portal.invokeFactory('AWSFile', 'aws_file')
        aws_file = getattr(self.portal, fid)
        aws_file.update(file=self._get_image())
        self.assertEqual(aws_file.portal_type, 'AWSFile')

        self.assert_(aws_file.schema['file'].url(
            aws_file).startswith('http://contentfiles.s3.amazonaws.com/'))

    def test_AWSFileUpdate(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)

        fid = self.portal.invokeFactory('AWSFile', 'aws_file')
        aws_file = getattr(self.portal, fid)
        aws_file.update(file=self._get_image())

        # check if data attribute is empty
        self.assert_(aws_file.getField('file').get(aws_file).data)

        # update aws file with new file
        aws_file.update(file=self._get_image(filename='aws.gif'))

        # check if data attribute is empty
        value = aws_file.getField('file').get(aws_file)
        self.assert_(not value.__dict__['data'])

        # update file when aws is turned off
        self.conf_sheet._updateProperty('USE_AWS', False)
        aws_file.update(file=self._get_image())

        # check if file field attribute value has proper type (File)
        value = aws_file.getField('file').get(aws_file)
        self.assert_(isinstance(value, File))

        # check if data attribute is not empty
        self.assert_(value.data)

        # update file when aws is turned on
        self.conf_sheet._updateProperty('USE_AWS', True)
        aws_file.update(file=self._get_image(filename='aws.gif'))

        # check if file field attribute value has proper type (AWSFile)
        value = aws_file.getField('file').get(aws_file)
        self.assert_(isinstance(value, AWSFile))
        self.assert_(not 'data' in value.__dict__)

        # update file when there is problems with amazon
        self.conf_sheet._updateProperty('AWS_KEY_ID', 'BAD_KEY')
        aws_file.update(file=self._get_image())

        # check if file field attribute value has proper type (File)
        value = aws_file.getField('file').get(aws_file)
        self.assert_(isinstance(value, File))
        self.assert_(value.data)


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSFileTestCase))
    return suite
