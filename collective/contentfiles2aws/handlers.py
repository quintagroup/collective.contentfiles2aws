from zope.component import getUtility

from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.interfaces import IAWSUtility
from collective.contentfiles2aws.client.awsclient import \
        AWSFileClientRemoveError

def before_file_remove(obj, event):
    aws_utility = getUtility(IAWSUtility)
    as3client = aws_utility.getFileClient()
    file_obj = obj.getFile()
    if file_obj.uploaded_source_id:
        try:
            as3client.delete(file_obj.uploaded_source_id)
        except AWSFileClientRemoveError, e:
            IStatusMessage(obj.REQUEST).addStatusMessage(_(e.message),
                                                         type='error')
            obj.REQUEST.RESPONSE.redirect(obj.absolute_url())

