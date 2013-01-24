import os
from cgi import escape
from types import FileType
from cStringIO import StringIO

from OFS.Image import File
from OFS.Image import Image
from OFS.Image import Pdata
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from ZODB.POSException import ConflictError
from ZPublisher.HTTPRequest import FileUpload

from zope.contenttype import guess_content_type

from Products.Archetypes.utils import shasattr
from Products.Archetypes.Field import FileField
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Archetypes.debug import log
from Products.Archetypes.debug import log_exc
from Products.Archetypes.Registry import registerField
from Products.Archetypes.Storage import AttributeStorage
from Products.Archetypes.interfaces.base import IBaseUnit
from Products.Archetypes.exceptions import FileFieldException
from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.awsimage import AWSImage
from collective.contentfiles2aws.widgets import AWSFileWidget
from collective.contentfiles2aws.widgets import AWSImageWidget

from collective.contentfiles2aws.config import AWSCONF_SHEET
from collective.contentfiles2aws.client.fsclient import FileClientStoreError
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError

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

    _properties = FileField._properties.copy()
    _properties.update({
        'widget' : AWSFileWidget,
        'content_class' : AWSFile,
        'fallback_content_class': File,
        })

    security  = ClassSecurityInfo()

    def use_aws(self, instance):
        pp = getToolByName(instance, 'portal_properties')
        awsconf_sheet = getattr(pp, AWSCONF_SHEET)
        return awsconf_sheet.getProperty('USE_AWS')

    def migrate(self, instance):
        if not self.use_aws(instance):
            return

        obj = self.get(instance)
        if hasattr(obj, 'meta_type') and \
            obj.meta_type == self.fallback_content_class.meta_type:
            return True
        else:
            return False

    def _do_migrate(self, instance):
        id = self.getName()
        file_obj = self.getStorage(instance).get(id, instance,
                                              raw=True, unwrapped=True)
        if file_obj.meta_type != self.fallback_content_class.meta_type:
            return

        filename = getattr(file_obj, 'filename', '')
        content_type = getattr(file_obj, 'content_type', '')
        try:
            obj = self._make_file(id, title='', file='',
                                   filename=filename,
                                   content_type=content_type,
                                   instance=instance)
            self.getStorage(instance).set(id, instance, obj)
            fobj = self.getStorage(instance).get(id, instance)
            fobj.manage_upload(file_obj.data)
        except FileClientStoreError:
            self.getStorage(instance).set(id, instance, file_obj,
                                          filename=filename,
                                          content_type=content_type)

    def unset(self, instance, **kwargs):
        __traceback_info__ = (self.getName(), instance, kwargs)
        self.getStorage(instance).unset(self.getName(), instance, **kwargs)

    security.declarePrivate('_set')
    def _set(self, instance, value, **kwargs):
        kwargs['field'] = self
        # Remove acquisition wrappers
        value = aq_base(value)
        __traceback_info__ = (self.getName(), instance, value, kwargs)
        self.getStorage(instance).set(self.getName(), instance,
                                        value, **kwargs)

    def _get(self, instance, **kwargs):
        #TODO: this method is from ObjectField class
        #      does it really need to be customized?
        __traceback_info__ = (self.getName(), instance, kwargs)
        try:
            kwargs['field'] = self
            return self.getStorage(instance).get(self.getName(), instance, **kwargs)
        except AttributeError:
            # happens if new Atts are added and not yet stored in the instance
            # @@ and at every other possible occurence of an AttributeError?!!
            default = self.getDefault(instance)
            if not kwargs.get('_initializing_', False):
                self.set(instance, default, _initializing_=True, **kwargs)
            return default

    def get(self, instance, **kwargs):
        if instance.REQUEST.get('%s_migrate' % self.getName(), ''):
            self._do_migrate(instance)

        value = self._get(instance, **kwargs)
        if value and not isinstance(value, self.content_class) and \
                not isinstance(value, self.fallback_content_class):
            value = self._wrapValue(instance, value)
        if (shasattr(value, '__of__', acquire=True)
            and not kwargs.get('unwrapped', False)):
            return value.__of__(instance)
        else:
            return value

    def _make_file(self, id, title='', file='', filename=u'',
                   content_type='', instance=None, factory=None):
        """File content factory"""


        if not factory:
            factory = self.content_class

        if not self.use_aws(instance):
            factory = self.fallback_content_class

        if factory == self.fallback_content_class:
            if not file:
                file = StringIO()
            file_obj =  factory(id, title, file, content_type=content_type)
            setattr(file_obj, 'filename', filename)
        else:
            file_obj = factory(id, title, file, filename=filename,
                               content_type=content_type)

        return file_obj

    security.declarePrivate('set')
    def set(self, instance, value, **kwargs):
        """
        Assign input value to object. If mimetype is not specified,
        pass to processing method without one and add mimetype returned
        to kwargs. Assign kwargs to instance.
        """
        if value == "DELETE_FILE":
            if shasattr(instance, '_FileField_types'):
                delattr(aq_base(instance), '_FileField_types')
            self.unset(self, instance, **kwargs)
            return

        if not kwargs.has_key('mimetype'):
            kwargs['mimetype'] = None

        kwargs['default'] = self.getDefault(instance)
        initializing = kwargs.get('_initializing_', False)

        if not initializing:
            file = self.get(instance, raw=True, unwrapped=True)
        else:
            file = None
        factory = self.content_class
        if not initializing and not isinstance(file, factory):
            # Convert to same type as factory
            # This is here mostly for backwards compatibility
            v, m, f = self._migrate_old(file, **kwargs)
            kwargs['mimetype'] = m
            kwargs['filename'] = f
            obj = self._wrapValue(instance, v, **kwargs)
            # Store so the object gets a _p_jar,
            # if we are using a persistent storage, that is.
            self._set(instance, obj, **kwargs)
            file = self.get(instance, raw=True, unwrapped=True)
            # Should be same as factory now, but if it isn't, that's
            # very likely a bug either in the storage implementation
            # or on the field implementation.

        value, mimetype, filename = self._process_input(value, file=file,
                                                        instance=instance,
                                                        **kwargs)

        kwargs['mimetype'] = mimetype
        kwargs['filename'] = filename

        # remove ugly hack
        if shasattr(instance, '_FileField_types'):
            del instance._FileField_types
        if value is None:
            # do not send None back as file value if we get a default (None)
            # value back from _process_input.  This prevents
            # a hard error (NoneType object has no attribute 'seek') from
            # occurring if someone types in a bogus name in a file upload
            # box (at least under Mozilla).
            value = ''
        if value.meta_type == self.fallback_content_class.meta_type:
            # there was error during file upload and we are using
            # fallback factory, so we set object as is.
            self._set(instance, value, **kwargs)
            return
        obj = self._wrapValue(instance, value, **kwargs)
        self._set(instance, obj, **kwargs)

    def url(self, instance):
        fobj = self.get(instance, raw=True, unwrapped=True)
        if hasattr(fobj, 'meta_type') and \
            fobj.meta_type == self.fallback_content_class.meta_type:
            return '%s/at_download/%s' % (instance.absolute_url(),
                                          self.getName())
        return fobj.absolute_url()

    def _process_input(self, value, file=None, default=None, mimetype=None,
                       instance=None, filename='', **kwargs):
        if file is None:
            file = self._make_file(self.getName(), title='',
                                   file='', instance=instance)
        if IBaseUnit.isImplementedBy(value):
            mimetype = value.getContentType() or mimetype
            filename = value.getFilename() or filename
            value = value.getRaw()
        elif isinstance(value, self.content_class):
            filename = getattr(value, 'filename', value.getId())
            mimetype = getattr(value, 'content_type', mimetype)
            return value, mimetype, filename
        elif isinstance(value, File):
            # In case someone changes the 'content_class'
            filename = getattr(value, 'filename', value.getId())
            mimetype = getattr(value, 'content_type', mimetype)
            value = value.data
        elif isinstance(value, FileUpload) or shasattr(value, 'filename'):
            filename = value.filename
        elif isinstance(value, FileType) or shasattr(value, 'name'):
            # In this case, give preference to a filename that has
            # been detected before. Usually happens when coming from PUT().
            if not filename:
                filename = value.name
                # Should we really special case here?
                for v in (filename, repr(value)):
                    # Windows unnamed temporary file has '<fdopen>' in
                    # repr() and full path in 'file.name'
                    if '<fdopen>' in v:
                        filename = ''
        elif isinstance(value, basestring):
            # Let it go, mimetypes_registry will be used below if available
            pass
        elif (isinstance(value, Pdata) or (shasattr(value, 'read') and
                                           shasattr(value, 'seek'))):
            # Can't get filename from those.
            pass
        elif value is None:
            # Special case for setDefault
            value = ''
        else:
            klass = getattr(value, '__class__', None)
            raise FileFieldException('Value is not File or String (%s - %s)' %
                                     (type(value), klass))
        filename = filename[max(filename.rfind('/'),
                                filename.rfind('\\'),
                                filename.rfind(':'),
                                )+1:]

        setattr(file, 'filename', filename)
        initializing = kwargs.get('_initializing_', False)
        if not initializing:
            try:
                file.manage_upload(value)
            except (FileClientRemoveError, FileClientStoreError), e:
                request = instance.REQUEST
                IStatusMessage(request).addStatusMessage(
                        u"Couldn't update %s file to storage. %s" % \
                                (safe_unicode(filename),
                                 safe_unicode(e.message)), type='error')
                #creating default OFS.Image.File object to prevent data loss
                file = self._make_file(self.getName(),
                                       title='', file='', filename=filename,
                                       instance=instance,
                                       factory=self.fallback_content_class)
                file.manage_upload(value)

        if mimetype is None or mimetype == 'text/x-unknown-content-type':
            body = file.data
            if not isinstance(body, basestring):
                body = body.data
            mtr = getToolByName(instance, 'mimetypes_registry', None)
            if mtr is not None:
                kw = {'mimetype':None,
                      'filename':filename}
                # this may split the encoded file inside a multibyte character
                try:
                    d, f, mimetype = mtr(body[:8096], **kw)
                except UnicodeDecodeError:
                    d, f, mimetype = mtr(len(body) < 8096 and body or '', **kw)
            else:
                mimetype = getattr(file, 'content_type', None)
                if mimetype is None:
                    mimetype, enc = guess_content_type(filename, body, mimetype)
        # mimetype, if coming from request can be like:
        # text/plain; charset='utf-8'
        mimetype = str(mimetype).split(';')[0].strip()
        setattr(file, 'content_type', mimetype)
        return file, mimetype, filename

registerField(AWSFileField,
              title='AWS File',
              description='Used for storing files in amazon s3 service.')


class AWSImageField(AWSFileField):
    _properties = AWSFileField._properties.copy()
    _properties.update({
        'type' : 'image',
        'default' : '',
        'original_size': None,
        'max_size': None,
        'sizes' : {'thumb':(80,80)},
        'swallowResizeExceptions' : False,
        'pil_quality' : 88,
        'pil_resize_algo' : PIL_ALGO,
        'default_content_type' : 'image/png',
        'allowable_content_types' : ('image/gif','image/jpeg','image/png'),
        'widget': AWSImageWidget,
        'storage': AttributeStorage(),
        'content_class': AWSImage,
        'fallback_content_class': Image,
        })

    security  = ClassSecurityInfo()

    default_view = "view"

    def _do_migrate(self, instance):
        id = self.getName()
        image = self.getStorage(instance).get(id, instance,
                                              raw=True, unwrapped=True)
        if not isinstance(image, self.fallback_content_class):
            return

        filename = getattr(image, 'filename', '')
        content_type = getattr(image, 'content_type','')
        try:
            obj = self._make_file(id, title='', file='',
                                   filename=filename,
                                   content_type=content_type,
                                   instance=instance)
            self.getStorage(instance).set(id, instance, obj)
            img = self.getStorage(instance).get(id, instance)
            img.manage_upload(str(image.data))
            self.createScales(instance, value=str(image.data),
                              filename=filename, migrate=True)
        except FileClientStoreError:
            self.getStorage(instance).set(id, instance, image,
                                          filename=filename,
                                          content_type=content_type)

    def _wrapValue(self, instance, value, **kwargs):
        """Wraps the value in the content class if it's not wrapped
        """
        if isinstance(value, self.content_class) or \
                isinstance(value, self.fallback_content_class):
            return value
        mimetype = kwargs.get('mimetype', self.default_content_type)
        filename = kwargs.get('filename', '')
        obj = self._make_file(self.getName(),
                              title='', file=value, instance=instance)
        setattr(obj, 'filename', filename)
        setattr(obj, 'content_type', mimetype)
        try:
            delattr(obj, 'title')
        except (KeyError, AttributeError):
            pass

        return obj

    security.declarePrivate('set')
    def set(self, instance, value, **kwargs):
        if value=="DELETE_IMAGE":
            self.removeScales(instance, **kwargs)
            # unset main field too
            self._unset(self, instance, **kwargs)
            return

        kwargs.setdefault('mimetype', None)
        default = self.getDefault(instance)

        initializing = kwargs.get('_initializing_', False)
        if not initializing:
            file = self.get(instance, raw=True, unwrapped=True)
        else:
            file = None
        factory = self.content_class
        if not initializing and not isinstance(file, factory):
            # Convert to same type as factory
            # This is here mostly for backwards compatibility
            v, m, f = self._migrate_old(file, **kwargs)
            kwargs['mimetype'] = m
            kwargs['filename'] = f
            obj = self._wrapValue(instance, v, **kwargs)
            # Store so the object gets a _p_jar,
            # if we are using a persistent storage, that is.
            self._set(instance, obj, **kwargs)
            file = self.get(instance, raw=True, unwrapped=True)
            # Should be same as factory now, but if it isn't, that's
            # very likely a bug either in the storage implementation
            # or on the field implementation.

        value, mimetype, filename = self._process_input(value, file=file,
                                                        default=default,
                                                        instance=instance,
                                                        **kwargs)
        if filename:
            self.filename = filename

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
        self.createOriginal(instance, value, **kwargs)
        self.createScales(instance, value=data, filename=filename)

    security.declareProtected(permissions.View, 'getAvailableSizes')
    def getAvailableSizes(self, instance):
        """Get sizes

        Supports:
            self.sizes as dict
            A method in instance called like sizes that returns dict
            A callable
        """
        sizes = self.sizes
        if isinstance(sizes, dict):
            return sizes
        elif isinstance(sizes, basestring):
            assert(shasattr(instance, sizes))
            method = getattr(instance, sizes)
            data = method()
            assert(isinstance(data, dict))
            return data
        elif callable(sizes):
            return sizes()
        elif sizes is None:
            return {}
        else:
            raise TypeError, 'Wrong self.sizes has wrong type: %s' % type(sizes)

    security.declareProtected(permissions.ModifyPortalContent, 'rescaleOriginal')
    def rescaleOriginal(self, value, **kwargs):
        """rescales the original image and sets the data

        for self.original_size or self.max_size

        value must be an OFS.Image.Image instance
        """
        data = str(value.data)
        if not HAS_PIL:
            return data

        mimetype = kwargs.get('mimetype', self.default_content_type)

        if self.original_size or self.max_size:
            if not value:
                return self.default
            w=h=0
            if self.max_size:
                if value.width > self.max_size[0] or \
                       value.height > self.max_size[1]:
                    factor = min(float(self.max_size[0])/float(value.width),
                                 float(self.max_size[1])/float(value.height))
                    w = int(factor*value.width)
                    h = int(factor*value.height)
            elif self.original_size:
                w,h = self.original_size
            if w and h:
                __traceback_info__ = (self, value, w, h)
                fvalue, format = self.scale(data, w, h)
                data = fvalue.read()
        else:
            data = str(value.data)

        return data

    security.declarePrivate('createOriginal')
    def createOriginal(self, instance, value, **kwargs):
        """create the original image (save it)
        """
        if value:
            image = self._wrapValue(instance, value, **kwargs)
        else:
            image = self.getDefault(instance)

        self._set(instance, image, **kwargs)

    security.declarePrivate('removeScales')
    def removeScales(self, instance, **kwargs):
        """Remove the scaled image
        """
        sizes = self.getAvailableSizes(instance)
        if sizes:
            for name, size in sizes.items():
                id = self.getScaleName(instance, scale=name)
                try:
                    # the following line may throw exceptions on types, if the
                    # type-developer add sizes to a field in an existing
                    # instance and a user try to remove an image uploaded before
                    # that changed. The problem is, that the behavior for non
                    # existent keys isn't defined. I assume a keyerror will be
                    # thrown. Ignore that.
                    image = self.getStorage(instance).get(id, instance)
                    if isinstance(image, self.content_class):
                        image.remove_source()
                    self.getStorage(instance).unset(id, instance, **kwargs)
                except KeyError:
                    pass

    security.declareProtected(permissions.ModifyPortalContent, 'createScales')
    def createScales(self, instance, value=_marker,
                     filename='', migrate=False):
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

        if not filename:
            filename = self.getFilename(instance)

        for n, size in sizes.items():
            if size == (0,0):
                continue
            w, h = size
            id = self.getScaleName(instance, scale=n)
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
            try:
                image = self.getStorage(instance).get(id, instance)
            except AttributeError:
                image = None

            if image:
                if migrate and isinstance(image, self.fallback_content_class):
                    image = self._make_file(id, title='', file='',
                                             instance=instance,
                                             filename=filename,
                                             content_type=mimetype)
                    self.getStorage(instance).set(id, instance, image)
                    image = self.getStorage(instance).get(id, instance)
                    image.manage_upload(imgdata)
                    continue
                else:
                    try:
                        image.filename = filename
                        image.manage_upload(imgdata)
                        continue
                    except (FileClientRemoveError, FileClientStoreError), e:
                        image = self._make_file(id, title='', file=imgdata,
                                               instance=instance,
                                               filename=filename,
                                               content_type=mimetype,
                                               factory=self.fallback_content_class)
            else:
                try:
                    image = self._make_file(id, title=self.getName(),
                                            file='', filename=filename,
                                            content_type=mimetype,
                                            instance=instance)
                    self.getStorage(instance).set(id, instance, image)
                    image = self.getStorage(instance).get(id, instance)
                    image.manage_upload(imgdata)
                    continue
                except (FileClientRemoveError, FileClientStoreError), e:
                    request = instance.REQUEST
                    IStatusMessage(request).addStatusMessage(
                            u"Couldn't update %s file to storage. %s" % \
                                    (safe_unicode(filename),
                                    safe_unicode(e.message)), type='error')
                    # creating default OFS.Image.Image object
                    # to prevent data loss
                    image = self._make_file(id, title='', file=imgdata,
                                            instance=instance,
                                            filename=filename,
                                            content_type=mimetype,
                                            factory=self.fallback_content_class)
            try:
                delattr(image, 'title')
            except (KeyError, AttributeError):
                pass
            # manually use storage
            self.getStorage(instance).set(id, instance, image,
                                          mimetype=mimetype, filename=filename)

    security.declarePrivate('scale')
    def scale(self, data, w, h, default_format = 'PNG'):
        """ scale image (with material from ImageTag_Hotfix)"""
        #make sure we have valid int's
        size = int(w), int(h)

        original_file=StringIO(data)
        image = PIL.Image.open(original_file)
        # consider image mode when scaling
        # source images can be mode '1','L,','P','RGB(A)'
        # convert to greyscale or RGBA before scaling
        # preserve palletted mode (but not pallette)
        # for palletted-only image formats, e.g. GIF
        # PNG compression is OK for RGBA thumbnails
        original_mode = image.mode
        if original_mode == '1':
            image = image.convert('L')
        elif original_mode == 'P':
            image = image.convert('RGBA')
        image.thumbnail(size, self.pil_resize_algo)
        format = image.format and image.format or default_format
        # decided to only preserve palletted mode
        # for GIF, could also use image.format in ('GIF','PNG')
        if original_mode == 'P' and format == 'GIF':
            image = image.convert('P')
        thumbnail_file = StringIO()
        # quality parameter doesn't affect lossless formats
        image.save(thumbnail_file, format, quality=self.pil_quality)
        thumbnail_file.seek(0)
        return thumbnail_file, format.lower()

    security.declareProtected(permissions.View, 'getSize')
    def getSize(self, instance, scale=None):
        """get size of scale or original
        """
        img = self.getScale(instance, scale=scale)
        if not img:
            return 0, 0
        return img.width, img.height

    security.declareProtected(permissions.View, 'getScale')
    def getScale(self, instance, scale=None, **kwargs):
        """Get scale by name or original
        """
        if scale is None:
            return self.get(instance, **kwargs)
        else:
            assert(scale in self.getAvailableSizes(instance).keys(),
                   'Unknown scale %s for %s' % (scale, self.getName()))
            id = self.getScaleName(instance, scale=scale)
            try:
                image = self.getStorage(instance).get(id, instance, **kwargs)
            except AttributeError:
                return ''
            image = self._wrapValue(instance, image, **kwargs)
            if shasattr(image, '__of__', acquire=True) and not kwargs.get('unwrapped', False):
                return image.__of__(instance)
            else:
                return image

    security.declareProtected(permissions.View, 'getScaleName')
    def getScaleName(self, instance, scale=None):
        """Get the full name of the attribute for the scale
        """
        if scale:
            return '%s_%s' % (self.getName(), scale)
        else:
            return ''

    security.declarePublic('get_size')
    def get_size(self, instance):
        """Get size of the stored data used for get_size in BaseObject

        TODO: We should only return the size of the original image
        """
        sizes = self.getAvailableSizes(instance)
        original = self.get(instance)
        size = original and original.get_size() or 0

        if sizes:
            for name in sizes.keys():
                id = self.getScaleName(scale=name)
                try:
                    data = self.getStorage(instance).get(id, instance)
                except AttributeError:
                    pass
                else:
                    size+=data and data.get_size() or 0
        return size

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

    def _process_input(self, value, file=None, default=None, mimetype=None,
                       instance=None, filename='', **kwargs):
        if file is None:
            filename = getattr(value, 'filename', '')
            file = self._make_file(self.getName(),
                                    title='', file='', instance=instance)
        if IBaseUnit.isImplementedBy(value):
            mimetype = value.getContentType() or mimetype
            filename = value.getFilename() or filename
            value = value.getRaw()
        elif isinstance(value, self.content_class):
            filename = getattr(value, 'filename', value.getId())
            mimetype = getattr(value, 'content_type', mimetype)
            return value, mimetype, filename
        elif isinstance(value, File):
            # In case someone changes the 'content_class'
            filename = getattr(value, 'filename', value.getId())
            mimetype = getattr(value, 'content_type', mimetype)
            value = value.data
        elif isinstance(value, FileUpload) or shasattr(value, 'filename'):
            filename = value.filename
        elif isinstance(value, FileType) or shasattr(value, 'name'):
            # In this case, give preference to a filename that has
            # been detected before. Usually happens when coming from PUT().
            if not filename:
                filename = value.name
                # Should we really special case here?
                for v in (filename, repr(value)):
                    # Windows unnamed temporary file has '<fdopen>' in
                    # repr() and full path in 'file.name'
                    if '<fdopen>' in v:
                        filename = ''
        elif isinstance(value, basestring):
            # Let it go, mimetypes_registry will be used below if available
            pass
        elif (isinstance(value, Pdata) or (shasattr(value, 'read') and
                                           shasattr(value, 'seek'))):
            # Can't get filename from those.
            pass
        elif value is None:
            # Special case for setDefault
            value = ''
        else:
            klass = getattr(value, '__class__', None)
            raise FileFieldException('Value is not File or String (%s - %s)' %
                                     (type(value), klass))
        filename = filename[max(filename.rfind('/'),
                                filename.rfind('\\'),
                                filename.rfind(':'),
                                )+1:]

        setattr(file, 'filename', filename)
        initializing = kwargs.get('_initializing_', False)
        if not initializing:
            try:
                file.manage_upload(value)
            except (FileClientRemoveError, FileClientStoreError), e:
                request = instance.REQUEST
                IStatusMessage(request).addStatusMessage(
                        u"Couldn't update %s file to storage. %s" % \
                                (safe_unicode(filename),
                                 safe_unicode(e.message)), type='error')
                #creating default OFS.Image.File object to prevent data loss
                file = self._make_file(self.getName(),
                                       title='', file=value, instance=instance,
                                       filename=filename,
                                       content_type=mimetype,
                                       factory=self.fallback_content_class)

        if mimetype is None or mimetype == 'text/x-unknown-content-type':
            body = file.data
            if not isinstance(body, basestring):
                body = body.data
            mtr = getToolByName(instance, 'mimetypes_registry', None)
            if mtr is not None:
                kw = {'mimetype':None,
                      'filename':filename}
                # this may split the encoded file inside a multibyte character
                try:
                    d, f, mimetype = mtr(body[:8096], **kw)
                except UnicodeDecodeError:
                    d, f, mimetype = mtr(len(body) < 8096 and body or '', **kw)
            else:
                mimetype = getattr(file, 'content_type', None)
                if mimetype is None:
                    mimetype, enc = guess_content_type(filename, body, mimetype)
        # mimetype, if coming from request can be like:
        # text/plain; charset='utf-8'
        mimetype = str(mimetype).split(';')[0].strip()
        setattr(file, 'content_type', mimetype)
        return file, mimetype, filename

registerField(AWSImageField,
              title='AWS Image',
              description=('Used for storing images. '
                           'Images can then be retrieved in '
                           'different thumbnail sizes'))
