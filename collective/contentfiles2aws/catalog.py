from plone.indexer import indexer

from Products.Archetypes.interfaces import IBaseObject

from collective.contentfiles2aws.awsfile import AWSFile
from collective.contentfiles2aws.interfaces import IAWSField
from collective.contentfiles2aws.interfaces import IAWSImageField

@indexer(IBaseObject)
def aws_sources(obj):
    sids = {}
    if not hasattr(obj, 'schema'):
        return

    obj_fields = obj.schema.fields()
    for f in obj_fields:
        if IAWSField.providedBy(f):
            accessor= f.getAccessor(obj)
            field_content = accessor()
            if not isinstance(field_content, AWSFile):
                return

            fname = f.getName()
            sids[fname] = field_content.source_id
            if IAWSImageField.providedBy(f):
                for n in f.getAvailableSizes(obj).keys():
                    scale = f.getScale(obj, scale=n)
                    if isinstance(scale, AWSFile):
                      scale_name = '%s_%s' % (fname, n)
                      sids[scale_name] = scale.source_id
    if sids:
        return sids
