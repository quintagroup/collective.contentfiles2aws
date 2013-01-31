import transaction
from zope.component import getUtility

from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.interfaces import IAWSUtility
from collective.contentfiles2aws.interfaces import IAWSField
from collective.contentfiles2aws.interfaces import IAWSImageField
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError

def before_file_remove(obj, event):
    request = obj.REQUEST
    if request.ACTUAL_URL.endswith('delete_confirmation') and \
            request.get('REQUEST_METHOD') == 'GET':
                # delete event is fired by link integrity check, skip it.
                return

    # check if object has aws fileds
    obj_fields = obj.schema.fields()
    for f in obj_fields:
        if IAWSField.providedBy(f):
            aws_utility = getUtility(IAWSUtility)
            as3client = aws_utility.getFileClient()
            accessor= f.getAccessor(obj)
            field_content = accessor()
            if hasattr(field_content, 'uploaded_source_id') and\
                    field_content.uploaded_source_id:
                try:
                    as3client.delete(field_content.uploaded_source_id)
                    if IAWSImageField.providedBy(f):
                        f.removeScales(obj)
                except FileClientRemoveError, e:
                    IStatusMessage(obj.REQUEST).addStatusMessage(_(e.message),
                                                                 type='error')
                    transaction.abort()
                    obj.REQUEST.RESPONSE.redirect(obj.absolute_url())
