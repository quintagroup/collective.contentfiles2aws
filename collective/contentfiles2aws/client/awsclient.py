import urllib
import logging
from boto.exception import S3CopyError
from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection

from zope.interface import implements

from collective.contentfiles2aws.client.interfaces import IAWSFileClient
from collective.contentfiles2aws.client.fsclient import \
    FileClientRetrieveError, FileClientStoreError, FileClientRemoveError
from collective.contentfiles2aws.client.fsclient import FileClientCopyError

logger = logging.getLogger(__name__)


class AWSFileClientStoreError(FileClientStoreError):
    pass


class AWSFileClientRetrieveError(FileClientRetrieveError):
    pass


class AWSFileClientRemoveError(FileClientRemoveError):
    pass


class AWSFileClientCopyError(FileClientCopyError):
    pass


class AWSFileClient(object):
    """ Simple amazon s3 file client. """

    implements(IAWSFileClient)

    def __init__(self, aws_key_id, aws_seecret_key, bucket_name,
                 aws_filename_prefix=None):
        self._aws_key_id = aws_key_id
        self._aws_seecret_key = aws_seecret_key
        self.bucket_name = bucket_name
        self.connection = S3Connection(aws_key_id, aws_seecret_key)
        self.aws_filename_prefix = aws_filename_prefix

    def _get_bucket_name(self, **kw):
        bucket_name = self.bucket_name
        if hasattr(kw, 'bucket_name') and kw['bucket_name']:
            bucket_name = kw['bucket_name']
        return bucket_name

    def _get_key(self, filename):
        if not self.aws_filename_prefix:
            return filename
        return '%s/%s' % (self.aws_filename_prefix, filename)

    def get(self, filename, **kw):
        """ Get file with specified filename from amazon.

        Search file on amazon storage and if file with specified name
        exists returns file content.

        :param filename: name of file.
        :type filename: string
        :returns: file content in case file exists,
        ohterwise returns None

        """

        bucket_name = self._get_bucket_name(**kw)

        try:
            bucket = self.connection.get_bucket(bucket_name)
            key = bucket.get_key(self._get_key(filename))
            if key:
                return key.get_contents_as_string()
        except S3ResponseError, e:
            logger.exception('%s, %s, %s' % (e.status, e.reason, e.message))
            raise AWSFileClientRetrieveError(e.message)

    def put(self, filename, data, **kw):
        """Writes file to amazon storage under provided file name.

        :param filename: name of file.
        :type filename: string
        :param data: file content.
        :type: string: string
        :param kw: dictionary with file metadata
        :type kw: dict
        :returns: None

        """

        mimetype = None
        if 'mimetype' in kw and kw['mimetype']:
            mimetype = kw['mimetype']

        conn = self.connection
        bucket_name = self._get_bucket_name(**kw)
        try:
            if bucket_name in [b.name for b in conn.get_all_buckets()]:
                bucket = conn.get_bucket(bucket_name)
            else:
                bucket = conn.create_bucket(bucket_name)

            key = bucket.get_key(self._get_key(filename))
            if not key:
                key = bucket.new_key(self._get_key(filename))
            if mimetype:
                key.set_metadata('Content-Type', mimetype)
                mtype, msubtype = mimetype.split('/')
                if mtype != 'image':
                    # set content disposition metadata with original
                    # filename for files.
                    if 'original_name' in kw and kw['original_name']:
                        fname = urllib.quote(kw['original_name'])
                    else:
                        fname = '_'.join(filename.split('_')[3:])
                    key.set_metadata("Content-Disposition",
                                     "attachment; filename*=UTF-8''%s" % fname)
            key.set_contents_from_string(data)
            key.set_acl('public-read')
        except S3ResponseError, e:
            logger.exception('%s, %s, %s' % (e.status, e.reason, e.message))
            raise AWSFileClientStoreError(e.message)

    def delete(self, filename, **kw):
        """ Removes file form amazon storage using provided filename.

        :param filename: name of file.
        :type filename: string

        """

        bucket_name = self._get_bucket_name(**kw)
        try:
            bucket = self.connection.get_bucket(bucket_name)
            bucket.delete_key(self._get_key(filename))
        except S3ResponseError, e:
            logger.exception('%s, %s, %s' % (e.status, e.reason, e.message))
            raise AWSFileClientRemoveError(u"Couldn't delete %s file. %s" %
                                           (filename.decode('utf-8'),
                                            e.message and
                                            e.message.decode('utf-8') or ''))

    def source_url(self, filename, **kw):
        bucket_name = self._get_bucket_name(**kw)
        return "http://%s.%s/%s" % (bucket_name,
                                    self.connection.host,
                                    self._get_key(filename))

    def copy_source(self, filename, new_filename, **kw):
        """ Create a copy of specified file.

        :param filename: source file name
        :type filename: string
        :param new_filename: new file name
        :type new_filename: string

        """

        bucket_name = self._get_bucket_name(**kw)

        metadata = None
        if 'metadata' in kw:
            metadata = kw['metadata']

        try:
            bucket = self.connection.get_bucket(bucket_name)
            bucket.copy_key(self._get_key(new_filename), bucket_name,
                            self._get_key(filename), metadata=metadata)

            # copy permissions
            origin_key = bucket.get_key(self._get_key(filename))
            new_key = bucket.get_key(self._get_key(new_filename))
            new_key.set_acl(origin_key.get_acl())
        except (S3CopyError, S3ResponseError), e:
            logger.exception('%s, %s, %s' % (e.status, e.reason, e.message))
            raise AWSFileClientCopyError(
                u"Couldn't make copy for  %s file. %s" %
                (filename.decode('utf-8'), e.message.decode('utf-8')))
