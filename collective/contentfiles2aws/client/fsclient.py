class FileClientError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)

class FileClientRetrieveError(FileClientError):
    """ Base Retrieve Error Exception"""
    pass


class FileClientStoreError(FileClientError):
    """ Base Store Error Exception """
    pass


class FileClientRemoveError(FileClientError):
    """ Base Remove Error Exception """
    pass

class FileClientCopyError(FileClientError):
    """ Base Copy Error Exception """
    pass


class FSFileClient(object):
    pass
