from cgi import escape

from AccessControl import ClassSecurityInfo
from OFS.Image import Image

from zope.interface import implements

from Products.Archetypes.Field import FileField, ImageField
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.debug import log
from Products.Archetypes.Registry import registerField

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.widgets import AWSFileWidget
from collective.contentfiles2aws.widgets import AWSImageWidget
from collective.contentfiles2aws.interfaces import IAWSFileField
from collective.contentfiles2aws.interfaces import IAWSImageField
from collective.contentfiles2aws.config import AWSCONF_SHEET

_marker = []

try:
    import PIL.Image
except ImportError:
    # no PIL, no scaled versions!
    log("Warning: no Python Imaging Libraries (PIL) found." +
        "Archetypes based ImageField's don't scale if neccessary.")
    HAS_PIL = False
    PIL_ALGO = None
else:
    HAS_PIL = True
    PIL_ALGO = PIL.Image.ANTIALIAS


class AWSFileField(FileField):
    """Something that may be a file, but is not an image and doesn't
    want text format conversion"""

    implements(IAWSFileField)

    _properties = FileField._properties.copy()
    _properties.update({'widget': AWSFileWidget})

    security = ClassSecurityInfo()

    def getFilename(self, instance, fromBaseUnit=True):
        return self.get(instance).filename

    def use_aws(self, instance):
        pp = getToolByName(instance, 'portal_properties')
        awsconf_sheet = getattr(pp, AWSCONF_SHEET)
        return awsconf_sheet.getProperty('USE_AWS')

    def migrate(self, instance):
        if not self.use_aws(instance):
            return

        obj = self.get(instance)
        if isinstance(obj, AWSFile) or not obj:
            return False
        else:
            return True

    def url(self, instance):
        fobj = self.get(instance, raw=True, unwrapped=True)

        if isinstance(fobj, AWSFile):
            return fobj.absolute_url()

        return '%s/at_download/%s' % (instance.absolute_url(),
                                      self.getName())

registerField(AWSFileField,
              title='AWS File',
              description='Used for storing files in amazon s3 service.')


class AWSImageField(ImageField, AWSFileField):

    implements(IAWSImageField)

    _properties = ImageField._properties.copy()
    _properties.update({
        'widget': AWSImageWidget,
        'content_class': Image,
        'fallback_content_class': AWSFile})

    security = ClassSecurityInfo()

    default_view = "view"

    def _wrapValue(self, instance, value, **kwargs):
        """Wraps the value in the content class if it's not wrapped
        """
        if isinstance(value, self.content_class) or \
                isinstance(value, self.fallback_content_class):
            return value
        mimetype = kwargs.get('mimetype', self.default_content_type)
        filename = kwargs.get('filename', '')
        obj = self._make_file(self.getName(), title='',
                              file=value, instance=instance)
        setattr(obj, 'filename', filename)
        setattr(obj, 'content_type', mimetype)
        try:
            delattr(obj, 'title')
        except (KeyError, AttributeError):
            pass

        return obj

    security.declarePrivate('get')
    def get(self, instance, **kwargs):
        if not self.use_aws(instance):
            return ImageField.get(self, instance, **kwargs)

        request = instance.REQUEST
        if not isinstance(request, type('')) and \
                instance.REQUEST.get('%s_migrate' % self.getName(), ''):
            # migrate scales
            kwargs['migrate'] = True
            for n in self.getAvailableSizes(instance).keys():
                self.getScale(instance, scale=n, **kwargs)
        return ImageField.get(self, instance, **kwargs)

    security.declareProtected(permissions.View, 'tag')
    def tag(self, instance, scale=None, height=None, width=None, alt=None,
            css_class=None, title=None, **kwargs):
        """Create a tag including scale
        """

        image = self.getScale(instance, scale=scale)
        if not self.use_aws(instance) and not isinstance(image, AWSFile):
            return ImageField.tag(self, instance, scale=scale, height=height,
                                  width=width, alt=alt, css_class=css_class,
                                  title=title, **kwargs)
        if image:
            img_width, img_height = self.getSize(instance, scale=scale)
            url = image.absolute_url()
        else:
            img_height = 0
            img_width = 0
            url = instance.absolute_url()

        if height is None:
            height = img_height
        if width is None:
            width = img_width

        values = {'src': url,
                  'alt': escape(alt and alt or instance.Title(), 1),
                  'title': escape(title and title or instance.Title(), 1),
                  'height': height,
                  'width': width}

        result = '<img src="%(src)s" alt="%(alt)s" title="%(title)s" '\
                 'height="%(height)s" width="%(width)s"' % values

        if css_class is not None:
            result = '%s class="%s"' % (result, css_class)

        for key, value in kwargs.items():
            if value:
                result = '%s %s="%s"' % (result, key, value)

        return '%s />' % result

registerField(AWSImageField,
              title='AWS Image',
              description=('Used for storing images. '
                           'Images can then be retrieved in '
                           'different thumbnail sizes'))
