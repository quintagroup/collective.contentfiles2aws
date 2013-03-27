import os
import unittest2

from OFS.Image import File
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from plone.app.testing import setRoles, TEST_USER_ID

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

    def test_AWSFileCopy(self):
        self.conf_sheet._updateProperty('AWS_BUCKET_NAME', 'contentfiles')
        self.conf_sheet._updateProperty('USE_AWS', True)

        fid = self.portal.invokeFactory('AWSFile', 'aws_file')
        aws_file = getattr(self.portal, fid)
        aws_file.update(file=self._get_image())

        cp = self.portal.manage_copyObjects(ids=['aws_file'])

        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.manage_pasteObjects(cb_copy_data=cp)
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        original_source_id = aws_file.getField('file').get(aws_file).source_id

        aws_file_copy = getattr(self.portal, 'copy_of_aws_file')
        copy_source_id = \
                aws_file_copy.getField('file').get(aws_file_copy).source_id

        self.assertNotEqual(original_source_id, copy_source_id)

        # check that after original file remove we still have data in
        # cloned object.
        self.portal.manage_delObjects(ids=['aws_file'])
        self.assert_(aws_file_copy.getField('file').get(aws_file_copy).data)

        # check file copy handler when 'aws storage' is turned off.
        self.conf_sheet._updateProperty('USE_AWS', False)

        # lets make new copy from previous one.
        cp = self.portal.manage_copyObjects(ids=['copy_of_aws_file'])

        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.manage_pasteObjects(cb_copy_data=cp)
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        # ensure that copy object was successfuly removed.
        self.assert_('copy_2_of_aws_file' not in self.portal.objectIds())

        messages = IStatusMessage(self.layer['request']).showStatusMessages()
        error_message = ('Could not copy remote source. To be able to copy '
                        'object properly, please activate AWS storage')
        self.assert_(error_message in [m.message for m in messages])

        # check that folderish objects with aws files inside works properly.
        self.conf_sheet._updateProperty('USE_AWS', True)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.portal.invokeFactory('Folder', 'folder')
        folder = getattr(self.portal, 'folder')
        fid = folder.invokeFactory('AWSFile', 'aws_file')
        folder.aws_file.update(file=self._get_image())
        cp = self.portal.manage_copyObjects(ids=['folder'])

        self.portal.manage_pasteObjects(cb_copy_data=cp)

        folder_copy = getattr(self.portal, 'copy_of_folder')
        self.assert_('aws_file' in folder_copy.objectIds())

        aws_file = folder.aws_file
        aws_file_copy = folder_copy.aws_file

        original_source_id = aws_file.getField('file').get(aws_file).source_id
        copy_source_id = \
                aws_file_copy.getField('file').get(aws_file_copy).source_id

        self.assertNotEqual(original_source_id, copy_source_id)

        # check file copy handler for folderish objects
        # when 'aws storage' is turned off.
        self.conf_sheet._updateProperty('USE_AWS', False)

        cp = self.portal.manage_copyObjects(ids=['folder'])

        folder.manage_pasteObjects(cb_copy_data=cp)

        # ensure that copy object was successfuly removed.
        self.assert_('copy2_of_folder' not in folder.objectIds())

        messages = IStatusMessage(self.layer['request']).showStatusMessages()
        error_message = ('Could not copy remote source. To be able to copy '
                        'object properly, please activate AWS storage')
        self.assert_(error_message in [m.message for m in messages])

        setRoles(self.portal, TEST_USER_ID, ["Member"])


def test_suite():
    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(AWSFileTestCase))
    return suite
