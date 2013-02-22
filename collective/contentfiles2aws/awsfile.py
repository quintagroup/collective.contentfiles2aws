from OFS.Image import File
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view as View

from zope.component import getUtility

from collective.contentfiles2aws.interfaces import IAWSFileClientUtility


class AWSFile(File):
    """ Oject that represents AWS file."""

    meta_type = 'AWS File'
    filename = u''
    data = ''
    # for image files
    height=''
    width=''

    security = ClassSecurityInfo()

    def __init__(self, id, size=0,filename=u'', content_type=''):
        self.__name__ = id
        self.size = size
        self.filename = filename
        self.content_type = content_type
        self.source_id = None

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST, RESPONSE):
        """
        The default view of the contents of a File or Image.

        Returns the contents of the file or image.  Also, sets the
        Content-Type HTTP header to the objects content type.

        """
        return RESPONSE.redirect(self.absolute_url())

    def absolute_url(self):
        aws_utility = getUtility(IAWSFileClientUtility)
        as3client = aws_utility.getFileClient()
        return as3client.source_url(self.source_id)

    def remove_source(self):
        aws_utility = getUtility(IAWSFileClientUtility)
        as3client = aws_utility.getFileClient()
        if self.source_id:
            as3client.delete(self.source_id)
