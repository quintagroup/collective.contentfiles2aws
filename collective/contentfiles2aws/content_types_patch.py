from Products.ATContentTypes.content.file import ATFile, ATFileSchema
from Products.ATContentTypes.content.image import ATImage, ATImageSchema
from Products.ATContentTypes.content.newsitem import ATNewsItem, \
    ATNewsItemSchema
from Products.ATContentTypes import ATCTMessageFactory as _
from Products.validation import V_REQUIRED
from Products.ATContentTypes.config import PROJECTNAME
from Products.ATContentTypes.configuration import zconf
from Products.ATContentTypes.content.base import registerATCT

from collective.contentfiles2aws.fields import AWSFileField, AWSImageField
from collective.contentfiles2aws.widgets import AWSFileWidget, AWSImageWidget
from collective.contentfiles2aws.storage import AWSStorage


ATFileSchema = ATFileSchema.copy()
ATFileSchema['file'] = \
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
                        show_content_type = False,))

ATFile.schema = ATFileSchema
registerATCT(ATFile, PROJECTNAME)


ATImageSchema = ATImageSchema.copy()
ATImageSchema['image'] = \
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
                        show_content_type = False,))

ATImage.schema = ATImageSchema
registerATCT(ATImage, PROJECTNAME)



ATNewsItemSchema = ATNewsItemSchema.copy()
ATNewsItemSchema['image'] = \
    AWSImageField('image',
           required = False,
           storage = AWSStorage(migrate=True),
           languageIndependent = True,
           max_size = zconf.ATNewsItem.max_image_dimension,
           sizes= {'large'   : (768, 768),
                   'preview' : (400, 400),
                   'mini'    : (200, 200),
                   'thumb'   : (128, 128),
                   'tile'    :  (64, 64),
                   'icon'    :  (32, 32),
                   'listing' :  (16, 16),
                  },
           validators = (('isNonEmptyFile', V_REQUIRED),
                                ('checkNewsImageMaxSize', V_REQUIRED)),
           widget = AWSImageWidget(
               description = _(u'help_news_image', default=u'Will be shown in the news listing, and in the news item itself. Image will be scaled to a sensible size.'),
               label= _(u'label_news_image', default=u'Image'),
               show_content_type = False)
           )

ATNewsItem.schema = ATNewsItemSchema
registerATCT(ATNewsItem, PROJECTNAME)
