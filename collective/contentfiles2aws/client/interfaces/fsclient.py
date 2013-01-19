from zope.interface import Interface


class IFileClient(Interface):
    """ Simple file client."""

    def get(filename, **kw):
        """ Get file with specified filename.

        Search file in storage and if file with specified name
        exists returns file content.

        :param filename: name of file.
        :type filename: string
        :returns: file content in case file exists,
        ohterwise returns None

        """
    def put(filename, data, **kw):
        """Writes file to storage under provided file name.

        :param filename: name of file.
        :type filename: string
        :param mimetype: file mimetype.
        :type mimetype: string.
        :param data: file content.
        :type: string: string
        :returns: None

        """

    def delete(filename, **kw):
        """ Removes file form storage using provided filename.

        :param filename: name of file.
        :type filename: string

        """

