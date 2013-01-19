from zope.component import getUtility

from Globals import DTMLFile
from OFS.Image import File, cookId
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view as View

from collective.contentfiles2aws.interfaces import IAWSUtility

manage_addFileForm=DTMLFile('dtml/imageAdd', globals(),Kind='File',kind='file')
def manage_addFile(self,id,file='',title='',precondition='', content_type='',
                   REQUEST=None):
    """Add a new File object.

    Creates a new File object 'id' with the contents of 'file'"""

    id=str(id)
    title=str(title)
    content_type=str(content_type)
    precondition=str(precondition)

    id, title = cookId(id, title, file)

    self=self.this()

    # First, we create the file without data:
    self._setObject(id, AWSFile(id,title,'',content_type, precondition))

    # Now we "upload" the data.  By doing this in two steps, we
    # can use a database trick to make the upload more efficient.
    if file:
        self._getOb(id).manage_upload(file)
        #TODO: remove file object in case upload didn't finish sucessfuly
    if content_type:
        self._getOb(id).content_type=content_type

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(self.absolute_url()+'/manage_main')

class AWSFile(File):
    """ Oject that represents AWS file."""

    meta_type = 'AWS File'
    data = ''

    security = ClassSecurityInfo()

    def __init__(self, id, title, file, content_type='', precondition=''):
        self.__name__=id
        self.title=title
        self.precondition=precondition
        self.size = 0
        self.content_type = content_type
        self.uploaded_source_id = None

        #upload file to remote server only if it is not empty
        if file:
            data, size = self._read_data(file)
            content_type=self._get_content_type(file, data, id, content_type)
            if not self.source_id:
                self.source_id = getattr(file, 'filename')
            self.update_data(data, content_type, size)

    def getSourceId(self):
        fname = getattr(self, 'filename', '')
        return "%s_%s" % (self.id(), fname)

    def update_source(self, data, content_type):
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        if self.uploaded_source_id:
            # remove old object
            as3client.delete(aws_utility.getBucketName(),
                             self.uploaded_source_id)

        as3client.put(aws_utility.getBucketName(),
                      self.getSourceId(), content_type, data)
        as3client.set_permission(aws_utility.getBucketName(),
                                 self.getSourceId(), 'public-read')
        self.uploaded_source_id = self.getSourceId()

    def update_data(self, data, content_type=None, size=None):
        if isinstance(data, unicode):
            raise TypeError('Data can only be str or file-like.  '
                            'Unicode objects are expressly forbidden.')

        if content_type is not None: self.content_type=content_type
        if size is None: size=len(data)
        self.size=size

        # write file to amazon
        if isinstance(data, str):
            self.update_source(data, content_type)
            return

        #TODO: we need to find a way to upload file partially
        #      without loading whole file into memory.
        parts = []
        while data is not None:
            parts.append(data.data)
            data=data.next
        if parts:
            self.update_source(''.join(parts), content_type)

        self.ZCacheable_invalidate()
        self.ZCacheable_set(None)
        self.http__refreshEtag()

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST, RESPONSE):
        """
        The default view of the contents of a File or Image.

        Returns the contents of the file or image.  Also, sets the
        Content-Type HTTP header to the objects content type.
        """

        return RESPONSE.redirect(self.absolute_url())

    def absolute_url(self):
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        bucket_name = aws_utility.getBucketName()
        return as3client.absolute_url(bucket_name, self.getSourceId())
