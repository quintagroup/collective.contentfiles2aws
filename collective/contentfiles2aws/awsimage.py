from Globals import DTMLFile
from OFS.PropertyManager import PropertyManager
from AccessControl import ClassSecurityInfo
from AccessControl.Role import RoleManager
from AccessControl.Permissions import change_images_and_files
from AccessControl.Permissions import view_management_screens
from AccessControl.Permissions import view as View
from AccessControl.Permissions import ftp_access
from AccessControl.Permissions import delete_objects
from webdav.WriteLockInterface import WriteLockInterface
from OFS.SimpleItem import Item_w__name__
from OFS.Cache import Cacheable
from cgi import escape

from OFS.Image import getImageInfo, cookId

from collective.contentfiles2aws.awsfile import AWSFile


manage_addImageForm=DTMLFile('dtml/imageAdd',globals(),
                             Kind='Image',kind='image')
def manage_addImage(self, id, file, title='', precondition='', content_type='',
                    REQUEST=None):
    """
    Add a new AWSImage object.

    Creates a new Image object 'id' with the contents of 'file'.
    """

    id=str(id)
    title=str(title)
    content_type=str(content_type)
    precondition=str(precondition)

    id, title = cookId(id, title, file)

    self=self.this()

    # First, we create the image without data:
    self._setObject(id, AWSImage(id,title,'',content_type, precondition))

    # Now we "upload" the data.  By doing this in two steps, we
    # can use a database trick to make the upload more efficient.
    if file:
        self._getOb(id).manage_upload(file)
    if content_type:
        self._getOb(id).content_type=content_type

    if REQUEST is not None:
        try:    url=self.DestinationURL()
        except: url=REQUEST['URL1']
        REQUEST.RESPONSE.redirect('%s/manage_main' % url)
    return id


class AWSImage(AWSFile):
    """AWSImage objects can be GIF, PNG or JPEG and have the same methods
    as AWSFile objects.  Images also have a string representation that
    renders an HTML 'IMG' tag.
    """
    __implements__ = (WriteLockInterface,)
    meta_type='AWS Image'

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    filename = u''

    alt=''
    height=''
    width=''

    # FIXME: Redundant, already in base class
    security.declareProtected(change_images_and_files, 'manage_edit')
    security.declareProtected(change_images_and_files, 'manage_upload')
    security.declareProtected(change_images_and_files, 'PUT')
    security.declareProtected(View, 'index_html')
    security.declareProtected(View, 'get_size')
    security.declareProtected(View, 'getContentType')
    security.declareProtected(ftp_access, 'manage_FTPstat')
    security.declareProtected(ftp_access, 'manage_FTPlist')
    security.declareProtected(ftp_access, 'manage_FTPget')
    security.declareProtected(delete_objects, 'DELETE')

    _properties=({'id':'title', 'type': 'string'},
                 {'id':'alt', 'type':'string'},
                 {'id':'content_type', 'type':'string','mode':'w'},
                 {'id':'height', 'type':'string'},
                 {'id':'width', 'type':'string'},
                 )

    manage_options=(
        ({'label':'Edit', 'action':'manage_main',
         'help':('OFSP','Image_Edit.stx')},
         {'label':'View', 'action':'view_image_or_file',
         'help':('OFSP','Image_View.stx')},)
        + PropertyManager.manage_options
        + RoleManager.manage_options
        + Item_w__name__.manage_options
        + Cacheable.manage_options
        )

    manage_editForm  =DTMLFile('dtml/imageEdit',globals(),
                               Kind='Image',kind='image')
    manage_editForm._setName('manage_editForm')

    security.declareProtected(View, 'view_image_or_file')
    view_image_or_file =DTMLFile('dtml/imageView',globals())

    security.declareProtected(view_management_screens, 'manage')
    security.declareProtected(view_management_screens, 'manage_main')
    manage=manage_main=manage_editForm
    manage_uploadForm=manage_editForm

    security.declarePrivate('update_data')
    def update_data(self, data, content_type=None, size=None):
        if isinstance(data, unicode):
            raise TypeError('Data can only be str or file-like.  '
                            'Unicode objects are expressly forbidden.')

        if size is None: size=len(data)

        self.size=size
        self.data=data

        ct, width, height = getImageInfo(data)
        if ct:
            content_type = ct
        if width >= 0 and height >= 0:
            self.width = width
            self.height = height

        # Now we should have the correct content type, or still None
        if content_type is not None: self.content_type = content_type

        if isinstance(data, str):
            self.update_source(data, content_type)
            return

        parts = []
        while data is not None:
            parts.append(data.data)
            data=data.next
        if parts:
            self.update_source(''.join(parts), content_type)

        self.ZCacheable_invalidate()
        self.ZCacheable_set(None)
        self.http__refreshEtag()

    def __str__(self):
        return self.tag()

    security.declareProtected(View, 'tag')
    def tag(self, height=None, width=None, alt=None,
            scale=0, xscale=0, yscale=0, css_class=None, title=None, **args):
        """
        Generate an HTML IMG tag for this image, with customization.
        Arguments to self.tag() can be any valid attributes of an IMG tag.
        'src' will always be an absolute pathname, to prevent redundant
        downloading of images. Defaults are applied intelligently for
        'height', 'width', and 'alt'. If specified, the 'scale', 'xscale',
        and 'yscale' keyword arguments will be used to automatically adjust
        the output height and width values of the image tag.

        Since 'class' is a Python reserved word, it cannot be passed in
        directly in keyword arguments which is a problem if you are
        trying to use 'tag()' to include a CSS class. The tag() method
        will accept a 'css_class' argument that will be converted to
        'class' in the output tag to work around this.
        """
        if height is None: height=self.height
        if width is None:  width=self.width

        # Auto-scaling support
        xdelta = xscale or scale
        ydelta = yscale or scale

        if xdelta and width:
            width =  str(int(round(int(width) * xdelta)))
        if ydelta and height:
            height = str(int(round(int(height) * ydelta)))

        result='<img src="%s"' % (self.absolute_url())

        if alt is None:
            alt=getattr(self, 'alt', '')
        result = '%s alt="%s"' % (result, escape(alt, 1))

        if title is None:
            title=getattr(self, 'title', '')
        result = '%s title="%s"' % (result, escape(title, 1))

        if height:
            result = '%s height="%s"' % (result, height)

        if width:
            result = '%s width="%s"' % (result, width)

        # Omitting 'border' attribute (Collector #1557)
#        if not 'border' in [ x.lower() for x in  args.keys()]:
#            result = '%s border="0"' % result

        if css_class is not None:
            result = '%s class="%s"' % (result, css_class)

        for key in args.keys():
            value = args.get(key)
            if value:
                result = '%s %s="%s"' % (result, key, value)

        return '%s />' % result
