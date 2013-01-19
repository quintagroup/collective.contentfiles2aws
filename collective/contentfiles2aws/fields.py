from types import FileType

from OFS.Image import File
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from ZPublisher.HTTPRequest import FileUpload

from zope.contenttype import guess_content_type

from Products.Archetypes.utils import shasattr
from Products.Archetypes.Field import FileField
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.Registry import registerField
from Products.Archetypes.interfaces.base import IBaseUnit
from Products.Archetypes.exceptions import FileFieldException

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.widgets import AWSFileWidget


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
        if value and not isinstance(value, self.content_class):
            value = self._wrapValue(instance, value)
        if (shasattr(value, '__of__', acquire=True)
            and not kwargs.get('unwrapped', False)):
            return value.__of__(instance)
        else:
            return value

    def _make_file(self, id, title='', file='', instance=None):
        """File content factory"""
        source_id = ''
        if file:
            source_id = self.cookFileId(instance)
        return self.content_class(id, source_id, title, file)

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
