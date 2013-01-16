from zope.component import getUtility

from Globals import DTMLFile
from OFS.Image import File, cookId

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

    def __init__(self, id, title, file, content_type='', precondition=''):
        super(AWSFile, self).__init__(id, title, file,
                                      content_type=content_type,
                                      precondition=precondition)

    def update_data(self, data, content_type=None, size=None):
        if isinstance(data, unicode):
            raise TypeError('Data can only be str or file-like.  '
                            'Unicode objects are expressly forbidden.')

        if content_type is not None: self.content_type=content_type
        if size is None: size=len(data)
        self.size=size

        # write file to amazon
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        if isinstance(data, str):
            as3client.put(aws_utility.getBucketName(), self.id(),
                          content_type, data)
            return

        #TODO: we need to find a way to upload file partially
        #      without loading whole file into memory.
        parts = []
        while data is not None:
            parts.append(data.data)
            data=data.next
        if parts:
            as3client.put(aws_utility.getBucketName(), self.id(),
                          content_type, ''.join(parts))

        self.ZCacheable_invalidate()
        self.ZCacheable_set(None)
        self.http__refreshEtag()
