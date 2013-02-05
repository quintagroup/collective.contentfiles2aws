from zope.interface import implements

from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import PrimaryFieldMarshaller

from Products.ATContentTypes.content.base import registerATCT
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.content.file import ATFile

from Products.ATContentTypes import ATCTMessageFactory as _
from Products.validation import V_REQUIRED

from collective.contentfiles2aws.config import PROJECTNAME
from collective.contentfiles2aws.storage import AWSStorage
from collective.contentfiles2aws.fields import AWSFileField
from collective.contentfiles2aws.widgets import AWSFileWidget
from collective.contentfiles2aws.content.interfaces import IAWSFile


__docformat__ = 'restructuredtext'


AWSFileSchema = ATContentTypeSchema.copy() + Schema((
    AWSFileField('file',
              required=True,
              primary=True,
              searchable=False,
              languageIndependent=True,
              storage = AWSStorage(),
              validators = (('isNonEmptyFile', V_REQUIRED),
                             ('checkFileMaxSize', V_REQUIRED)),
              widget = AWSFileWidget(
                           description = '',
                           label=_(u'label_file', default=u'File'),
                           show_content_type = False,)),
    ), marshall=PrimaryFieldMarshaller()
    )

AWSFileSchema['title'].required = False
finalizeATCTSchema(AWSFileSchema)


class AWSFile(ATFile):
    """An external file uploaded to amazon."""

    schema         =  AWSFileSchema
    portal_type    = 'AWSFile'
    archetype_name = 'AWSFile'

    implements(IAWSFile)

registerATCT(AWSFile, PROJECTNAME)
