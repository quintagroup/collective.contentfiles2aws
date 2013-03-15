import transaction
from zope.annotation import IAnnotations
from zope.component import getUtility

from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.interfaces import IAWSField
from collective.contentfiles2aws.interfaces import IAWSImageField
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError
from collective.contentfiles2aws.client.fsclient import FileClientCopyError

def _abort_transaction(request):
    annotations = IAnnotations(request)
    annotations['abort_transaction'] = 1

def before_file_remove(obj, event):
    request = getattr(obj, 'REQUEST', '')
    if request and hasattr(request, 'ACTUAL_URL') and \
       request.ACTUAL_URL.endswith('delete_confirmation') and \
            request.get('REQUEST_METHOD') == 'GET':
                # delete event is fired by link integrity check, skip it.
                return

    # check if object has aws fileds
    obj_fields = obj.schema.fields()
    for f in obj_fields:
        if IAWSField.providedBy(f):
            accessor= f.getAccessor(obj)
            field_content = accessor()
            if not isinstance(field_content, AWSFile):
                # nothing to do
                return
            aws_utility = getUtility(IAWSFileClientUtility)
            if not aws_utility.active():
                message = ("Could not delete remote source. "
                           "To be able to delete object properly, "
                           "please activate AWS storage")
                IStatusMessage(obj.REQUEST).addStatusMessage(_(message),
                                                             type='error')
                _abort_transaction(obj.REQUEST)
                return
            as3client = aws_utility.getFileClient()
            if hasattr(field_content, 'source_id') and field_content.source_id:
                try:
                    as3client.delete(field_content.source_id)
                    if IAWSImageField.providedBy(f):
                        f.removeScales(obj)
                except FileClientRemoveError, e:
                    IStatusMessage(obj.REQUEST).addStatusMessage(_(e.message),
                                                                 type='error')
                    _abort_transaction(obj.REQUEST)
                    obj.REQUEST.RESPONSE.redirect(obj.absolute_url())

def abort_remove(obj, event):
    annotations = IAnnotations(obj.REQUEST)
    if annotations and annotations.has_key('abort_transaction') and \
            annotations['abort_transaction']:
        transaction.abort()

def object_cloned(obj, event):

    def clone_source(aws_file, obj):
        old_sid = aws_file.source_id
        old_uid = old_sid.split('_')[0]
        new_sid = old_sid.replace(old_uid, obj.UID())

        as3client = aws_utility.getFileClient()
        as3client.copy_source(old_sid, new_sid)
        aws_file.source_id = new_sid

    obj_fields = obj.schema.fields()
    for f in obj_fields:
        if IAWSField.providedBy(f):
            accessor= f.getAccessor(obj)
            field_content = accessor()
            if not isinstance(field_content, AWSFile):
                # nothing to do
                continue
            else:
                aws_utility = getUtility(IAWSFileClientUtility)
                if not aws_utility.active():
                    message = ("Could not copy remote source. "
                               "To be able to copy object properly, "
                               "please activate AWS storage")
                    IStatusMessage(obj.REQUEST).addStatusMessage(_(message),
                                                                 type='error')
                    transaction.abort()
                    return
                if hasattr(field_content, 'source_id') and \
                        field_content.source_id:
                    try:
                        clone_source(field_content, obj)
                        if IAWSImageField.providedBy(f):
                            for n in f.getAvailableSizes(obj).keys():
                                clone_source(f.getScale(obj, scale=n), obj)
                    except FileClientCopyError, e:
                        IStatusMessage(obj.REQUEST).addStatusMessage(
                                _(e.message), type='error')
                        transaction.abort()
