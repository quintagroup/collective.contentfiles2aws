from zope.component import getUtility

from Products.Five.browser import BrowserView

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility


class AWSUtilView(BrowserView):
    """ Helper view.  """

    def getFieldValue(self, instance, name):
        field = instance.schema[name]
        accessor = field.getAccessor(instance)
        return accessor()

    def getUrlFromBrain(self, brain, name):
        if hasattr(brain, 'aws_sources') and brain.aws_sources:
            sid = brain.aws_sources[name]
            aws_utility = getUtility(IAWSFileClientUtility)
            bucket_name = aws_utility.getBucketName()
            client = aws_utility.getFileClient()
            url = "http://%s.%s" % (bucket_name, client.connection.server)

            filename_prefix = aws_utility.getAWSFilenamePrefix()
            if filename_prefix:
                url = '%s/%s' % (url, filename_prefix)

            url = '%s/%s' % (url, sid)
        else:
            url = '%s/%s' % (brain.getURL(), name)
        return url

    def getUrlFromObject(self, instance, name):
        value = self.getFieldValue(instance, name)
        if isinstance(value, AWSFile):
            url = value.absolute_url()
        else:
            url = '%s/%s' % (instance.absolute_url(), name)
        return url

    def get_file_url(self, instance, name='file', brain=True):
        """ Generates url for file stored in field. """

        return brain and self.getUrlFromBrain(instance, name) or \
            self.getUrlFromObject(instance, name)

    def get_image_url(self, instance, name='image', scale=None, brain=True):
        """ Generates url for file stored in field. """

        if scale:
            name = '%s_%s' % (name, scale)

        return brain and self.getUrlFromBrain(instance, name) or \
            self.getUrlFromObject(instance, name)
