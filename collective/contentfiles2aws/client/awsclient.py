import logging
from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection

from zope.interface import implements

from collective.contentfiles2aws.client.interfaces import IAWSFileClient
from collective.contentfiles2aws.client.fsclient import \
    FileClientRetrieveError, FileClientStoreError, FileClientRemoveError

logger = logging.getLogger(__name__)


class AWSFileClientStoreError(FileClientStoreError):
    pass


class AWSFileClientRetrieveError(FileClientRetrieveError):
    pass


class AWSFileClientRemoveError(FileClientRemoveError):
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
        :param mimetype: file mimetype.
        :type mimetype: string.
        :param data: file content.
        :type: string: string
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
            raise AWSFileClientRemoveError(u"Couldn't delete %s file. %s" % \
                                           (filename.decode('utf-8'),
                                            e.message.decode('utf-8')))

    def source_url(self, filename, **kw):
        bucket_name = self._get_bucket_name(**kw)
        return "http://%s.%s/%s" % (bucket_name,
                                    self.connection.server,
                                    self._get_key(filename))
