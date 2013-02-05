from zope.interface import implements
from zope.app.component.hooks import getSite

from Products.CMFCore.utils import getToolByName

from collective.contentfiles2aws.client import AWSFileClient
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.config import AWSCONF_SHEET


class AWSFileClientUtility(object):
    """
    """
    implements(IAWSFileClientUtility)

    def active(self):
        pp = getToolByName(getSite(), 'portal_properties')
        awsconf_sheet = getattr(pp, AWSCONF_SHEET)
        return awsconf_sheet.getProperty('USE_AWS')

    def getAWSConfiguration(self):
        """ Collect configuration infomation for aws client. """
        #TODO: temporary we will save configuration in property sheet.
        #      it will be good to have more flexible solution for this.
        pp = getToolByName(getSite(), 'portal_properties')
        awsconf_sheet = getattr(pp, AWSCONF_SHEET)
        aws_key_id = awsconf_sheet.getProperty('AWS_KEY_ID')
        aws_seecret_key = awsconf_sheet.getProperty('AWS_SEECRET_KEY')
        aws_bucket_name = awsconf_sheet.getProperty('AWS_BUCKET_NAME')
        aws_filename_prefix = awsconf_sheet.getProperty('AWS_FILENAME_PREFIX')

        return {'aws_key_id':aws_key_id,
                'aws_seecret_key':aws_seecret_key,
                'aws_bucket_name':aws_bucket_name,
                'aws_filename_prefix':aws_filename_prefix}

    def getBucketName(self):
        return self.getAWSConfiguration()['aws_bucket_name']

    def getAWSFilenamePrefix(self):
        return self.getAWSConfiguration()['aws_filename_prefix']

    def getFileClient(self):
        """ Provide an aws file client. """
        config = self.getAWSConfiguration()
        client = AWSFileClient(config['aws_key_id'],
                               config['aws_seecret_key'],
                               config['aws_bucket_name'])
        return client

aws_utility = AWSFileClientUtility()
