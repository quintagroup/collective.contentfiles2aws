import logging
from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection

logger = logging.getLogger(__name__)


class AWSFileClient(object):
    """ Simple amazon s3 file client. """

    def __init__(self, aws_key_id, aws_seecret_key):
        self._aws_key_id = aws_key_id
        self._aws_seecret_key = aws_seecret_key
        self.connection = S3Connection(aws_key_id, aws_seecret_key)

    def get(self, bucket_name, filename):
        """ Get file with specified filename from amazon.

        Search file on amazon storage and if file with specified name
        exists returns file content.

        :param bucket_name: amazon bucket name.
        :type bucket_name: string
        :param filename: name of file.
        :type filename: string
        :returns: file content in case file exists,
        ohterwise returns None

        """

        try:
            bucket = self.connection.get_bucket(bucket_name)
        except S3ResponseError, e:
            # we got nonexistent bucket name
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            return


        key = bucket.get_key(filename)
        if key:
            return key.get_contents_as_string()

    def put(self, bucket_name, filename, mimetype, data):
        """Writes file to amazon storage under provided file name.

        :param bucket_name: amazon bucket name.
        :type bucket_name: string
        :param filename: name of file.
        :type filename: string
        :param mimetype: file mimetype.
        :type mimetype: string.
        :param data: file content.
        :type: string: string
        :returns: None

        """

        conn = self.connection
        try:
            if bucket_name in [b.name for b in conn.get_all_buckets()]:
                bucket = conn.get_bucket(bucket_name)
            else:
                bucket = conn.create_bucket(bucket_name)
        except S3ResponseError,e:
            #XXX: think about what we should do in this case.
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

        try:
            key = bucket.get_key(filename)
            if not key:
                key = bucket.new_key(filename)
            key.set_metadata('Content-Type', mimetype)
            key.set_contents_from_string(data)
        except S3ResponseError:
            #XXX: think about what we should do in this case.
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

    def set_permission(self, bucket_name, filename, acl_string):
        conn = self.connection
        try:
            bucket = conn.get_bucket(bucket_name)
        except S3ResponseError,e:
            #XXX: think about what we should do in this case.
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

        try:
            key = bucket.get_key(filename)
            if not key:
                return
            key.set_acl(acl_string)
        except S3ResponseError:
            #XXX: think about what we should do in this case.
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

    def absolute_url(self, bucket_name, filename):
        return "http://%s.%s/%s" % (bucket_name,
                                    self.connection.server,
                                    filename)

    def delete(self, bucket_name, filename):
        """ Removes file form amazon storage using provided filename.

        :param bucket_name: amazon bucket name.
        :type bucket_name: string
        :param filename: name of file.
        :type filename: string

        """

        try:
            bucket = self.connection.get_bucket(bucket_name)
        except S3ResponseError, e:
            #XXX: think what we should do in this case.
            # we got nonexistent bucket name
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

        try:
            bucket.delete_key(filename)
        except S3ResponseError:
            #XXX: think what we should do in this case.
            logger.error('%s, %s, %s' % (e.status, e.reason, e.message))
            raise

    #TODO:implement metadata retrieving
    # perhaps we need to create own file like object with
    # all metadata inside.
    #def getFileInfo(self, filename):

    #    """ Collects information about file."""

    #    info = {}
    #    try:
    #        key = self.storage.get_key(self.key(filename))
    #    except S3ResponseError:
    #        logger.error(''.join(format_exception(*sys.exc_info())))
    #    else:
    #        if key:
    #            lm = parser.parse(key.last_modified)
    #            info['last_modify'] = lm.replace(tzinfo=None)
    #            return info

#TODO:implemnet this if needed
#    def list(self):
#        """ Return list of contained files. """
#
#        try:
#            return self.storage.list(self._key_prefix)
#        except S3ResponseError:
#            logger.error(''.join(format_exception(*sys.exc_info())))
#            return []

#if __name__ == '__main__':
    #client = AWSFileClient('xxxxx',
    #                       'xxxxx')
    #fileo = client.put('images.choosehelp.com', 'test/test.txt', 'text/plain', 'test content')
    #client.delete('images.choosehelp.com'
