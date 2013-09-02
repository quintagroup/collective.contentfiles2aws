import transaction

from Acquisition import aq_inner
from Acquisition import aq_parent
from zope.annotation import IAnnotations
from zope.component import getUtility

from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from collective.contentfiles2aws import utils
from collective.contentfiles2aws import MFactory as _
from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.interfaces import IAWSImageField
from collective.contentfiles2aws.client.fsclient import FileClientRemoveError
from collective.contentfiles2aws.client.fsclient import FileClientCopyError
from collective.contentfiles2aws.config import ABORT_TRANSACTION_FLAG
from collective.contentfiles2aws.config import SKIP_SOURCE_REMOVE_FLAG

class AWSSourceRemoveError(Exception):
    pass

class AWSSourceCopyError(Exception):
    pass

def remove_source(obj):
    """ Remove file data from amazon.

    :param obj: content object.

    """
    obj_fields = utils.getAWSFields(obj)
    for field, value in obj_fields:
       aws_utility = getUtility(IAWSFileClientUtility)
       if not aws_utility.active():
           raise AWSSourceRemoveError("Could not delete remote source. "
                                      "To be able to delete object properly, "
                                      "please activate AWS storage")
       as3client = aws_utility.getFileClient()
       if hasattr(value, 'source_id') and value.source_id:
           try:
               as3client.delete(value.source_id)
               if IAWSImageField.providedBy(field):
                   field.removeScales(obj)
           except FileClientRemoveError, e:
               raise AWSSourceRemoveError(e.message)

def clone_source(obj):
    """ Creates copy of file data on amazon.

    :param obj: content object.
    :param remove_origin: if set to true origin source will be removed.
    :type remove_origin: boolean

    """

    def copy_source(aws_file, obj):
        old_sid = aws_file.source_id
        new_sid = utils.replace_source_uid(old_sid, obj.UID())

        if old_sid == new_sid:
            # source already cloned
            return

        as3client = aws_utility.getFileClient()
        as3client.copy_source(old_sid, new_sid)
        aws_file.source_id = new_sid

    obj_fields = utils.getAWSFields(obj)
    for field, value in obj_fields:
        aws_utility = getUtility(IAWSFileClientUtility)
        if not aws_utility.active():
            raise AWSSourceCopyError("Could not copy remote source. "
                                     "To be able to copy object properly, "
                                     "please activate AWS storage")
        if hasattr(value, 'source_id') and \
                value.source_id:
            try:
                copy_source(value, obj)
                if IAWSImageField.providedBy(field):
                    for n in field.getAvailableSizes(obj).keys():
                        copy_source(field.getScale(obj, scale=n), obj)
            except (FileClientCopyError, FileClientRemoveError), e:
                raise AWSSourceCopyError(e.message)

def before_file_remove(obj, event):
    request = getattr(obj, 'REQUEST', '')
    if request and hasattr(request, 'ACTUAL_URL') and \
       request.ACTUAL_URL.endswith('delete_confirmation') and \
            request.get('REQUEST_METHOD') == 'GET':
                # delete event is fired by link integrity check, skip it.
                return

    # skip source remove if we have appropriate flag set in request
    annotations = IAnnotations(request)
    if annotations and annotations.has_key(SKIP_SOURCE_REMOVE_FLAG) and \
            annotations[SKIP_SOURCE_REMOVE_FLAG]:
        return

    try:
        remove_source(obj)
    except AWSSourceRemoveError, e:
        IStatusMessage(request).addStatusMessage(_(e), type='error')
        utils.abort_transaction(request)

def abort_remove(obj, event):
    annotations = IAnnotations(obj.REQUEST)
    if annotations and annotations.has_key(ABORT_TRANSACTION_FLAG) and \
            annotations[ABORT_TRANSACTION_FLAG]:
        transaction.abort()

def object_cloned(obj, event):

    def cleanup(obj):
        catalog = getToolByName(obj, 'portal_catalog')
        container = aq_parent(aq_inner(obj))
        # we have to skip source remove to be able to remove object.
        utils.skip_source_remove(obj.REQUEST)
        catalog.uncatalog_object('/'.join(obj.getPhysicalPath()))
        for brain in catalog(path={'depth': 1,
            'query': '/'.join(obj.getPhysicalPath())}):
            catalog.uncatalog_object(brain.getPath())
        container.manage_delObjects(ids=[obj.getId()])

    request = obj.REQUEST
    try:
        clone_source(obj)
    except AWSSourceCopyError, e:
        cleanup(obj)
        if aq_parent(aq_inner(obj)) is event.object:
            # clean up parent object
            cleanup(event.object)
        IStatusMessage(request).addStatusMessage(_(e), type='error')
        request.RESPONSE.redirect(request.get('HTTP_REFERER'))
