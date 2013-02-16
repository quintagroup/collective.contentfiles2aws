from zope.component import getUtility

from Products.Five.browser import BrowserView

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility


class AWSUtilView(BrowserView):
    """ Helper view.  """

    def getFieldValue(self, instance, name, scale=None):
        field = instance.getField(name)
        if scale:
            return field.getScale(instance, scale=scale)

        accessor = field.getAccessor(instance)
        return accessor()

    def getUrlFromBrain(self, brain, name, scale=None):
        if scale:
            name = '%s_%s' % (name, scale)

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

    def getUrlFromObject(self, instance, name, scale=None):
        value = self.getFieldValue(instance, name, scale=scale)
        if isinstance(value, AWSFile):
            url = value.absolute_url()
        else:
            url = '%s/%s_%s' % (instance.absolute_url(), name, scale)
        return url

    def get_file_url(self, instance, name='file', brain=True):
        """ Generates url for file stored in field. """

        return brain and self.getUrlFromBrain(instance, name) or \
            self.getUrlFromObject(instance, name)

    def get_image_url(self, instance, name='image', scale=None, brain=True):
        """ Generates url for file stored in field. """

        return brain and self.getUrlFromBrain(instance, name, scale=scale) or \
            self.getUrlFromObject(instance, name, scale=scale)
