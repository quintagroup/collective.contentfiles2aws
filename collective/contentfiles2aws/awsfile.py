from cgi import escape

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

    security.declareProtected(View, 'tag')
    def tag(self, height=None, width=None, alt=None,
            scale=0, xscale=0, yscale=0, css_class=None, title=None, **args):

        if not (self.height or self.width):
            # this is file not image
            return ''

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

        if css_class is not None:
            result = '%s class="%s"' % (result, css_class)

        for key in args.keys():
            value = args.get(key)
            if value:
                result = '%s %s="%s"' % (result, key, value)

        return '%s />' % result
