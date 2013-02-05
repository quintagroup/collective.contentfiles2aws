from Products.Archetypes.atapi import Schema
from Products.ATContentTypes.content.file import ATFile
from Products.ATContentTypes.content.image import ATImage
from Products.Archetypes.atapi import PrimaryFieldMarshaller
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes import ATCTMessageFactory as _
from Products.validation import V_REQUIRED
from Products.ATContentTypes.config import PROJECTNAME
from Products.ATContentTypes.configuration import zconf
from Products.ATContentTypes.content.base import registerATCT

from collective.contentfiles2aws.fields import AWSFileField, AWSImageField
from collective.contentfiles2aws.widgets import AWSFileWidget, AWSImageWidget
from collective.contentfiles2aws.storage import AWSStorage


ATFileSchema = ATContentTypeSchema.copy() + Schema((
    AWSFileField('file',
              required=True,
              primary=True,
              searchable=True,
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

ATFileSchema['title'].required = False
finalizeATCTSchema(ATFileSchema)

ATFile.schema = ATFileSchema
registerATCT(ATFile, PROJECTNAME)


ATImageSchema = ATContentTypeSchema.copy() + Schema((
    AWSImageField('image',
               required=True,
               primary=True,
               languageIndependent=True,
               storage = AWSStorage(),
               swallowResizeExceptions = zconf.swallowImageResizeExceptions.enable,
               pil_quality = zconf.pil_config.quality,
               pil_resize_algo = zconf.pil_config.resize_algo,
               max_size = zconf.ATImage.max_image_dimension,
               sizes= {'large'   : (768, 768),
                       'preview' : (400, 400),
                       'mini'    : (200, 200),
                       'thumb'   : (128, 128),
                       'tile'    :  (64, 64),
                       'icon'    :  (32, 32),
                       'listing' :  (16, 16),
                      },
               validators = (('isNonEmptyFile', V_REQUIRED),
                             ('checkImageMaxSize', V_REQUIRED)),
               widget = AWSImageWidget(
                        description = '',
                        label= _(u'label_image', default=u'Image'),
                        show_content_type = False,)),

    ), marshall=PrimaryFieldMarshaller()
    )

ATImageSchema['title'].required = False
finalizeATCTSchema(ATImageSchema)

ATImage.schema = ATImageSchema
registerATCT(ATImage, PROJECTNAME)
