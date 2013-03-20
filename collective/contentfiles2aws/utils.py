from zope.annotation import IAnnotations

from collective.contentfiles2aws import config
from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSField

def mark_request(request, name, value):
    annotations = IAnnotations(request)
    annotations[name] = value

def abort_transaction(request):
    mark_request(request, config.ABORT_TRANSACTION_FLAG, 1)

def skip_source_remove(request):
    mark_request(request, config.SKIP_SOURCE_REMOVE_FLAG, 1)

def replace_source_uid(sid, uid):
    old_uid = sid.split('_')[0]
    return  sid.replace(old_uid, uid)

def getAWSFields(obj):
    """ Collect aws fields for provided object.

    Goes through object schema fields and collects
    all aws fields.

    :param obj: content object.

    """
    aws_fields = []
    for f in obj.schema.fields():
        if IAWSField.providedBy(f):
            accessor= f.getAccessor(obj)
            field_content = accessor()
            if isinstance(field_content, AWSFile):
                aws_fields.append((f, field_content))
    return aws_fields
