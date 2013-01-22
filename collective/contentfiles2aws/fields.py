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

#from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.client.fsclient import FileClientStoreError

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

    def unset(self, instance, **kwargs):
        __traceback_info__ = (self.cookFileId(instance), instance, kwargs)
        self.getStorage(instance).unset(self.cookFileId(instance), instance, **kwargs)

    security.declarePrivate('_set')
    def _set(self, instance, value, **kwargs):
        kwargs['field'] = self
        # Remove acquisition wrappers
        value = aq_base(value)
        __traceback_info__ = (self.cookFileId(instance), instance, value, kwargs)
        self.getStorage(instance).set(self.cookFileId(instance), instance,
                                        value, **kwargs)

    def _get(self, instance, **kwargs):
        #TODO: this method is from ObjectField class
        #      does it really need to be customized?
        __traceback_info__ = (self.cookFileId(instance), instance, kwargs)
        try:
            kwargs['field'] = self
            return self.getStorage(instance).get(self.cookFileId(instance), instance, **kwargs)
        except AttributeError:
            # happens if new Atts are added and not yet stored in the instance
            # @@ and at every other possible occurence of an AttributeError?!!
            default = self.getDefault(instance)
            if not kwargs.get('_initializing_', False):
                self.set(instance, default, _initializing_=True, **kwargs)
            return default

    def get(self, instance, **kwargs):
        value = self._get(instance, **kwargs)
        if value and not isinstance(value, self.content_class) and \
                not isinstance(value, self.fallback_content_class):
            value = self._wrapValue(instance, value)
        if (shasattr(value, '__of__', acquire=True)
            and not kwargs.get('unwrapped', False)):
            return value.__of__(instance)
        else:
            return value

    def _make_file(self, id, title='', file='', instance=None, factory=None):
        """File content factory"""
        source_id = id
        if file:
            source_id = self.cookFileId(instance)
        if not factory:
            factory = self.content_class

        return factory(source_id, title, file)

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

    def cookFileId(self, instance):
        """ Prepare unique file id for file object. """
        return "%s_%s" %  (instance.UID(), self.getName())

    def url(self, instance):
        file_object = self.get(instance, raw=True, unwrapped=True)
        return file_object.absolute_url()

    def _process_input(self, value, file=None, default=None, mimetype=None,
                       instance=None, filename='', **kwargs):
        if file is None:
            file = self._make_file(self.cookFileId(instance), title='',
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
            except FileClientStoreError, e:
                request = instance.REQUEST
                IStatusMessage(request).addStatusMessage(
                        u"Couldn't store %s file to storage. %s" % \
                                (safe_unicode(filename),
                                 safe_unicode(e.message)), type='error')
                #creating default OFS.Image.File object to prevent data loss
                file = self._make_file(self.cookFileId(instance),
                                       title='', file='', instance=instance,
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
    """ implements an image attribute. it stores
        it's data in an image sub-object

        sizes is an dictionary containing the sizes to
        scale the image to. PIL is required for that.

        Format:
        sizes={'mini': (50,50),
               'normal' : (100,100), ... }
        syntax: {'name': (width,height), ... }

        the scaled versions can then be accessed as
        object/<imagename>_<scalename>

        e.g. object/image_mini

        where <imagename> is the fieldname and <scalename>
        is the name from the dictionary

        original_size -- this parameter gives the size in (w,h)
        to which the original image will be scaled. If it's None,
        then no scaling will take place.
        This is important if you don't want to store megabytes of
        imagedata if you only need a max. of 100x100 ;-)

        max_size -- similar to max_size but if it's given then the image
                    is checked to be no bigger than any of the given values
                    of width or height.

        example:

        ImageField('image',
            original_size=(600,600),
            sizes={ 'mini' : (80,80),
                    'normal' : (200,200),
                    'big' : (300,300),
                    'maxi' : (500,500)})

        will create an attribute called "image"
        with the sizes mini, normal, big, maxi as given
        and a original sized image of max 600x600.
        This will be accessible as
        object/image

        and the sizes as

        object/image_mini
        object/image_normal
        object/image_big
        object/image_maxi

        the official API to get tag (in a pagetemplate) is
        obj.getField('image').tag(obj, scale='mini')
        ...

        sizes may be the name of a method in the instance or a callable which
        returns a dict.

        Don't remove scales once they exist! Instead of removing a scale
        from the list of sizes you should set the size to (0,0). Thus
        removeScales method is able to find the scales to delete the
        data.

        Scaling will only be available if PIL is installed!

        If 'DELETE_IMAGE' will be given as value, then all the images
        will be deleted (None is understood as no-op)
        """

    # XXX__implements__ = FileField.__implements__ , IImageField

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

    def cookImageId(self, instance, filename=''):
        """ Prepare unique file id for file object. """
        if filename:
            return "%s_%s_%s" %  (instance.UID(), self.getName(), filename)
        return "%s_%s" %  (instance.UID(), self.getName())


    def _wrapValue(self, instance, value, **kwargs):
        """Wraps the value in the content class if it's not wrapped
        """
        if isinstance(value, self.content_class):
            return value
        mimetype = kwargs.get('mimetype', self.default_content_type)
        filename = kwargs.get('filename', '')
        obj = self._make_file(self.cookImageId(instance, filename=filename),
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
        if not value:
            return
        # Do we have to delete the image?
        if value=="DELETE_IMAGE":
            self.removeScales(instance, **kwargs)
            # unset main field too
            self._unset(self, instance, **kwargs)
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
        self.createOriginal(instance, value, **kwargs)
        self.createScales(instance, value=data)

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
        filename = getattr(self.get(instance), 'filename')
        fname, ext = os.path.splitext(filename)
        sizes = self.getAvailableSizes(instance)
        if sizes:
            for name, size in sizes.items():
                scale_name = '%s_%s%s' % (fname, n, ext)
                id = self.cookImageId(instance, filename=scale_name)
                try:
                    # the following line may throw exceptions on types, if the
                    # type-developer add sizes to a field in an existing
                    # instance and a user try to remove an image uploaded before
                    # that changed. The problem is, that the behavior for non
                    # existent keys isn't defined. I assume a keyerror will be
                    # thrown. Ignore that.
                    self.getStorage(instance).unset(id, instance, **kwargs)
                except KeyError:
                    pass

    security.declareProtected(permissions.ModifyPortalContent, 'createScales')
    def createScales(self, instance, value=_marker):
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

        filename = self.getFilename(instance)
        fname, ext = os.path.splitext(filename)

        for n, size in sizes.items():
            if size == (0,0):
                continue
            w, h = size
            scale_name = '%s_%s%s' % (fname, n, ext)
            id = self.cookImageId(instance, filename=scale_name)
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

    def _make_image(self, id, title='', file='',
                    content_type='', instance=None, factory=None):
        """Image content factory"""

        if not factory:
            factory = self.content_class

        return factory(id, title, file, content_type)

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
            id = self.getScaleName(scale=scale)
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
    def getScaleName(self, scale=None):
        """Get the full name of the attribute for the scale
        """
        if scale:
            return self.getName() + "_" + scale
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
        else:
            img_height=0
            img_width=0

        if height is None:
            height=img_height
        if width is None:
            width=img_width

        url = instance.absolute_url()
        if scale:
            url+= '/' + self.getScaleName(scale)
        else:
            url+= '/' + self.getName()

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
            file = self._make_image(self.cookImageId(instance,
                                                    filename=filename),
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
            except FileClientStoreError, e:
                request = instance.REQUEST
                IStatusMessage(request).addStatusMessage(
                        u"Couldn't store %s file to storage. %s" % \
                                (safe_unicode(filename),
                                 safe_unicode(e.message)), type='error')
                #creating default OFS.Image.File object to prevent data loss
                file = self._make_file(self.cookFileId(instance),
                                       title='', file='', instance=instance,
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

registerField(AWSImageField,
              title='AWS Image',
              description=('Used for storing images. '
                           'Images can then be retrieved in '
                           'different thumbnail sizes'))
