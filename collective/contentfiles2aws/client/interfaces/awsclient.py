from collective.contentfiles2aws.interfaces.file_client import IFileClient


class IAWSFileClient(IFileClient):
    """ File client for amazon s3 file storage.

    Here is described aws specific methods. For more general
    methods please see base interface.

    """

    def source_url(filename, **kw):
        """ Source url constructor.

        Build and return url to file source.

        """
