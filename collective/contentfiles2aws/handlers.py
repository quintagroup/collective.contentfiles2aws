import transaction
from zope.component import getUtility

from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.interfaces import IAWSUtility
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError

def before_file_remove(obj, event):
    aws_utility = getUtility(IAWSUtility)
    as3client = aws_utility.getFileClient()
    file_obj = obj.getFile()
    if hasattr(file_obj, 'uploaded_source_id') and file_obj.uploaded_source_id:
        try:
            as3client.delete(file_obj.uploaded_source_id)
        except FileClientRemoveError, e:
            IStatusMessage(obj.REQUEST).addStatusMessage(_(e.message),
                                                         type='error')
            transaction.abort()
            obj.REQUEST.RESPONSE.redirect(obj.absolute_url())


def before_image_remove(obj, event):
    aws_utility = getUtility(IAWSUtility)
    as3client = aws_utility.getFileClient()
    image_obj = obj.getImage()
    if hasattr(image_obj, 'uploaded_source_id') and image_obj.uploaded_source_id:
        try:
            as3client.delete(image_obj.uploaded_source_id)
            field = obj.schema['image']
            for scale in field.getAvailableSizes(obj):
                id = field.getScaleName(obj, scale=scale)
                as3client.delete(id)
        except FileClientRemoveError, e:
            IStatusMessage(obj.REQUEST).addStatusMessage(_(e.message),
                                                         type='error')
            transaction.abort()
            obj.REQUEST.RESPONSE.redirect(obj.absolute_url())

