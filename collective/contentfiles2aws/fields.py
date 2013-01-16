from OFS.Image import File
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo

from Products.Archetypes.utils import shasattr
from Products.Archetypes.Field import FileField
from Products.Archetypes.Registry import registerField

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
        fid = self.cookFileId(instance)
        return self.content_class(fid, title, file)

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
        return "%s%s" %  (instance.UID(), self.getName())


    def _wrapValue(self, instance, value, **kwargs):
        """Wraps the value in the content class if it's not wrapped
        """
        if isinstance(value, self.content_class):
            return value
        mimetype = kwargs.get('mimetype', self.default_content_type)
        filename = kwargs.get('filename', '')
        fid = self.cookFileId(instance)
        obj = self._make_file(fid, title='', file=value, instance=instance)
        setattr(obj, 'filename', filename)
        setattr(obj, 'content_type', mimetype)
        try:
            delattr(obj, 'title')
        except (KeyError, AttributeError):
            pass

        return obj


registerField(AWSFileField,
              title='AWS File',
              description='Used for storing files in amazon s3 service.')
