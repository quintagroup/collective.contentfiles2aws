from time import time
from md5 import md5
from random import random
from os.path import splitext

from OFS.Image import File, Image
from AccessControl import ClassSecurityInfo

from zope.component import getUtility

from Products.CMFPlone.utils import safe_unicode
from Products.statusmessages.interfaces import IStatusMessage
from Products.Archetypes.Storage.annotation import AnnotationStorage
from Products.Archetypes.interfaces import IReferenceable
from plone.i18n.normalizer.interfaces import IIDNormalizer

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.client.fsclient import FileClientStoreError
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError


class AWSStorage(AnnotationStorage):
    """ Archetype storage that stores data to amazon s3 service. """

    security = ClassSecurityInfo()

    def make_prefix(self):
        data = str(time() * 1000L) + str(random() * 100000000000000000L)
        return md5(data).hexdigest()[-7:]

    def getNormalizedName(self, filename):
        normalizer = getUtility(IIDNormalizer)
        return ".".join([normalizer.normalize(safe_unicode(n))
                         for n in splitext(filename)])

    def getSourceId(self, name, filename, instance, fresh=False):
        sid = ''
        if IReferenceable.providedBy(instance):
            sid = sid + instance.UID()
        sid = "%s_%s" % (sid, self.make_prefix())
        sid = "%s_%s" % (sid, name)
        fname = self.getNormalizedName(filename)
        if fname:
            sid = '%s_%s' % (sid, fname)
        return sid

    def update_source(self, file_, data, instance,
                      filename, content_type, width, height):
        aws_utility = getUtility(IAWSFileClientUtility)
        as3client = aws_utility.getFileClient()
        if file_.source_id:
            as3client.delete(file_.source_id)

        source_id = self.getSourceId(file_.id(), filename,
                                     instance, fresh=True)
        as3client.put(source_id, data, mimetype=content_type)
        setattr(file_, 'source_id', source_id)
        setattr(file_, 'size', len(data))
        setattr(file_, 'filename', filename)
        setattr(file_, 'content_type', content_type)

        if width and height:
            file_.width = width
            file_.height = height

    def _do_migrate(self, file_, instance, data=None, filename='',
                    content_type='', width='', height=''):
        if not data:
            data = file_.data

        if not filename:
            filename = getattr(file_, 'filename')

        if not content_type:
            content_type = getattr(file_, 'content_type')

        if not width:
            width = getattr(file_, 'width', '')

        if not height:
            height = getattr(file_, 'height', '')

        new_file = AWSFile(file_.id(), size=len(data),
                           filename=filename, content_type=content_type)
        try:
            self.update_source(new_file, data, instance,
                               filename, content_type, width, height)
            return new_file
        except (FileClientRemoveError, FileClientStoreError):
            # notify user???
            return file_

    security.declarePrivate('get')
    def get(self, name, instance, **kwargs):
        aws_utility = getUtility(IAWSFileClientUtility)
        if not aws_utility.active():
            return AnnotationStorage.get(self, name, instance, **kwargs)

        file_ = AnnotationStorage.get(self, name, instance, **kwargs)
        request = instance.REQUEST
        if not isinstance(request, type('')) and \
                request.get('%s_migrate' % name, '') or \
                ('migrate' in kwargs and kwargs['migrate']):
            # check if object is already migrated
            if isinstance(file_, AWSFile):
                return file_
            try:
                new_file_ = self._do_migrate(file_, instance)
            except (FileClientRemoveError, FileClientStoreError):
                return file_

            AnnotationStorage.set(self, name, instance, new_file_, **kwargs)
            return new_file_
        else:
            return file_

    security.declarePrivate('set')
    def set(self, name, instance, value, **kwargs):
        """Set a value under the key 'name' for retrevial by/for
        instance."""

        # collect value info
        filename = getattr(value, 'filename', '')
        content_type = getattr(value, 'content_type', '')
        width = getattr(value, 'width', '')
        height = getattr(value, 'height', '')

        aws_utility = getUtility(IAWSFileClientUtility)
        if not aws_utility.active():
            if isinstance(value, AWSFile):
                # use default OFS.Image or OFS.File
                if width and height:
                    # we have image
                    value = Image(value.id(), '', str(value.data),
                                  content_type=content_type)
                else:
                    value = File(value.id(), '', str(value.data),
                                 content_type=content_type)
                setattr(value, 'filename', filename)
            AnnotationStorage.set(self, name, instance, value, **kwargs)
            return

        try:
            file_ = self.get(name, instance, **kwargs)
        except AttributeError:
            file_ = None

        if file_:
            if isinstance(file_, AWSFile):
                try:
                    self.update_source(file_, value.data, instance,
                                       filename, content_type, width, height)
                except (FileClientRemoveError, FileClientStoreError), e:
                    request = instance.REQUEST
                    IStatusMessage(request).addStatusMessage(
                        u"Couldn't update %s file to storage. %s" %
                        (safe_unicode(filename),
                         safe_unicode(e.message)), type='error')
                    AnnotationStorage.set(self, name, instance,
                                          value, **kwargs)
            else:
                try:
                    file_ = self._do_migrate(file_, instance,
                                             data=value.data,
                                             filename=filename,
                                             content_type=content_type,
                                             width=width,
                                             height=height)
                except (FileClientRemoveError, FileClientStoreError):
                    request = instance.REQUEST
                    IStatusMessage(request).addStatusMessage(
                        u"Couldn't update %s file to storage. %s" %
                        (safe_unicode(filename),
                         safe_unicode(e.message)), type='error')
                    AnnotationStorage.set(self, name, instance,
                                          value, **kwargs)
                else:
                    AnnotationStorage.set(self, name, instance,
                                          file_, **kwargs)
        else:
            if value.size:
                file_ = AWSFile(name)
                try:
                    self.update_source(file_, value.data, instance,
                                       filename, content_type, width, height)
                except (FileClientRemoveError, FileClientStoreError), e:
                    request = instance.REQUEST
                    IStatusMessage(request).addStatusMessage(
                        u"Couldn't update %s file to storage. %s" %
                        (safe_unicode(filename),
                         safe_unicode(e.message)), type='error')

                    AnnotationStorage.set(self, name, instance,
                                          value, **kwargs)
                else:
                    AnnotationStorage.set(self, name, instance,
                                          file_, **kwargs)
            else:
                AnnotationStorage.set(self, name, instance, file_, **kwargs)

    security.declarePrivate('unset')
    def unset(self, name, instance, **kwargs):
        aws_utility = getUtility(IAWSFileClientUtility)
        if not aws_utility.active():
            return AnnotationStorage.unset(self, name, instance, **kwargs)

        file_ = self.get(name, instance, **kwargs)
        if isinstance(file_, AWSFile):
            file_.remove_source()
        AnnotationStorage.unset(self, name, instance, **kwargs)
