from time import time
from md5 import md5
from random import random
from os.path import splitext
from zope.component import getUtility
from Acquisition import aq_parent

from Globals import DTMLFile
from OFS.Image import File, cookId
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view as View

from Products.CMFPlone.utils import safe_unicode
from Products.Archetypes.interfaces import IReferenceable
from plone.i18n.normalizer.interfaces import IIDNormalizer

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
    self._setObject(id, AWSFile(id,title,'', content_type=content_type,
                    precondition=precondition))

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
    filename = u''

    security = ClassSecurityInfo()

    def __init__(self, id, title, file, filename=u'', content_type='',
                 precondition=''):
        self.__name__=id
        self.title=title
        self.size = 0
        self.filename = filename
        self.content_type = content_type
        self.precondition=precondition
        self.source_id = None
        self.uploaded_source_id = None


        if file:
            data, size = self._read_data(file)
            content_type=self._get_content_type(file, data, id, content_type)
            self.update_data(data, content_type, size)

    def make_prefix(self, *args):
        data =  str(time() * 1000L) + str(random()*100000000000000000L)
        return md5(data).hexdigest()[-7:]

    def getNormalizedName(self):
        if self.filename:
            normalizer = getUtility(IIDNormalizer)
            return ".".join([normalizer.normalize(safe_unicode(n))
                             for n in splitext(self.filename)])
    def getSourceId(self, fresh=False):
        if not fresh and self.source_id:
            return self.source_id

        sid = ''
        parent = aq_parent(self)
        if parent and IReferenceable.providedBy(parent):
            sid = sid + parent.UID()
        sid = sid + self.make_prefix()
        sid = "%s_%s" % (sid, self.id())
        fname = self.getNormalizedName()
        if fname:
            sid = '%s_%s' % (sid, fname)
        self.source_id = sid
        return self.source_id

    def update_source(self, data, content_type):
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        if self.uploaded_source_id:
            # remove old object
            as3client.delete(self.uploaded_source_id)

        source_id = self.getSourceId(fresh=True)
        as3client.put(source_id, data, mimetype=content_type)
        self.uploaded_source_id = source_id

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
        return as3client.source_url(self.getSourceId())

    def remove_source(self):
        aws_utility = getUtility(IAWSUtility)
        as3client = aws_utility.getFileClient()
        if self.uploaded_source_id:
            as3client.delete(self.uploaded_source_id)
