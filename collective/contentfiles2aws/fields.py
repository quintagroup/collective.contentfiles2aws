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
    log("Warning: no Python Imaging Libraries (PIL) found."+\
        "Archetypes based ImageField's don't scale if neccessary.")
    HAS_PIL=False
    PIL_ALGO = None
else:
    HAS_PIL=True
    PIL_ALGO = PIL.Image.ANTIALIAS


class AWSFileField(FileField):
    """Something that may be a file, but is not an image and doesn't
    want text format conversion"""

    implements(IAWSFileField)

    _properties = FileField._properties.copy()
    _properties.update({'widget' : AWSFileWidget})

    security  = ClassSecurityInfo()

    def use_aws(self, instance):
        pp = getToolByName(instance, 'portal_properties')
        awsconf_sheet = getattr(pp, AWSCONF_SHEET)
        return awsconf_sheet.getProperty('USE_AWS')

    def migrate(self, instance):
        if not self.use_aws(instance):
            return

        obj = self.get(instance)
        if isinstance(obj, AWSFile):
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


class AWSImageField(ImageField):

    implements(IAWSImageField)

    _properties = ImageField._properties.copy()
    _properties.update({
        'widget': AWSImageWidget,
        'content_class': Image,
        'fallback_content_class':AWSFile,
        })

    security  = ClassSecurityInfo()

    default_view = "view"

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
        if instance.REQUEST.get('%s_migrate' % self.getName(), ''):
            # migrate scales
            kwargs['migrate'] = True
            for n in self.getAvailableSizes(instance).keys():
                self.getScale(instance, scale=n, **kwargs)
        return ImageField.get(self, instance, **kwargs)

    def set(self, instance, value, **kwargs):
        if not value:
            return
        # Do we have to delete the image?
        if value=="DELETE_IMAGE":
            self.removeScales(instance, **kwargs)
            # unset main field too
            ObjectField.unset(self, instance, **kwargs)
            return

        kwargs.setdefault('mimetype', None)
        default = self.getDefault(instance)
        value, mimetype, filename = self._process_input(value, default=default,
                                                        instance=instance, **kwargs)
        # value is an OFS.Image.File based instance
        # don't store empty images
        get_size = getattr(value, 'get_size', None)
        if get_size is not None and get_size() == 0:
            return
        
        kwargs['mimetype'] = mimetype
        kwargs['filename'] = filename

        try:
            data = self.rescaleOriginal(value, **kwargs)
        except (ConflictError, KeyboardInterrupt):
            raise
        except:
            if not self.swallowResizeExceptions:
                raise
            else:
                log_exc()
                data = str(value.data)
        # TODO add self.ZCacheable_invalidate() later
        self.createOriginal(instance, data, **kwargs)
        self.createScales(instance, value=data, **kwargs)

    def createScales(self, instance, value=_marker, **kwargs):
        """creates the scales and save them
        """
        sizes = self.getAvailableSizes(instance)
        if not HAS_PIL or not sizes:
            return
        # get data from the original size if value is None
        if value is _marker:
            img = self.getRaw(instance)
            if not img:
                return
            data = str(img.data)
        else:
            data = value

        # empty string - stop rescaling because PIL fails on an empty string
        if not data:
            return

        if kwargs.has_key('filename') and kwargs['filename']:
            filename = kwargs['filename']
        else:
            filename = self.getFilename(instance)

        for n, size in sizes.items():
            if size == (0,0):
                continue
            w, h = size
            id = self.getName() + "_" + n
            __traceback_info__ = (self, instance, id, w, h)
            try:
                imgdata, format = self.scale(data, w, h)
            except (ConflictError, KeyboardInterrupt):
                raise
            except:
                if not self.swallowResizeExceptions:
                    raise
                else:
                    log_exc()
                    # scaling failed, don't create a scaled version
                    continue

            mimetype = 'image/%s' % format.lower()
            image = self._make_image(id, title=self.getName(), file=imgdata,
                                     content_type=mimetype, instance=instance)
            # nice filename: filename_sizename.ext
            #fname = "%s_%s%s" % (filename, n, ext)
            #image.filename = fname
            image.filename = filename
            try:
                delattr(image, 'title')
            except (KeyError, AttributeError):
                pass
            # manually use storage
            self.getStorage(instance).set(id, instance, image,
                                          mimetype=mimetype, filename=filename)

    security.declareProtected(permissions.View, 'tag')
    def tag(self, instance, scale=None, height=None, width=None, alt=None,
            css_class=None, title=None, **kwargs):
        """Create a tag including scale
        """
        image = self.getScale(instance, scale=scale)
        if image:
            img_width, img_height = self.getSize(instance, scale=scale)
            url = image.absolute_url()
        else:
            img_height=0
            img_width=0
            url = instance.absolute_url()

        if height is None:
            height=img_height
        if width is None:
            width=img_width

        values = {'src' : url,
                  'alt' : escape(alt and alt or instance.Title(), 1),
                  'title' : escape(title and title or instance.Title(), 1),
                  'height' : height,
                  'width' : width,
                 }

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
