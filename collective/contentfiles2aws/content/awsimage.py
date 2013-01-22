from zope.interface import implements

from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import PrimaryFieldMarshaller
from Products.Archetypes.atapi import AnnotationStorage

from Products.ATContentTypes.configuration import zconf
from Products.ATContentTypes.content.base import registerATCT
from Products.ATContentTypes.content.image import ATImage
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema

from Products.ATContentTypes import ATCTMessageFactory as _

from Products.validation.config import validation
from Products.validation.validators.SupplValidators import MaxSizeValidator
from Products.validation import V_REQUIRED

from collective.contentfiles2aws.config import PROJECTNAME
from collective.contentfiles2aws.fields import AWSImageField
from collective.contentfiles2aws.widgets import AWSImageWidget
from collective.contentfiles2aws.content.interfaces import IAWSImage


validation.register(MaxSizeValidator('checkImageMaxSize',
                                     maxsize=zconf.ATImage.max_file_size))


AWSImageSchema = ATContentTypeSchema.copy() + Schema((
    AWSImageField('image',
                  required=True,
                  primary=True,
                  languageIndependent=True,
                  storage = AnnotationStorage(migrate=True),
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

AWSImageSchema['title'].required = False
finalizeATCTSchema(AWSImageSchema)


class AWSImage(ATImage):
    """An image, which can be referenced in documents or 
       displayed in an album.

    """

    schema         =  AWSImageSchema

    portal_type    = 'AWSImage'
    archetype_name = 'AWSImage'

    implements(IAWSImage)


registerATCT(AWSImage, PROJECTNAME)
