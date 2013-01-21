from ZClasses import createZClassForBase
from AccessControl.Permissions import add_documents_images_and_files

from zope.i18nmessageid import MessageFactory

from Products.CMFCore import utils
from Products.Archetypes import atapi

from collective.contentfiles2aws.content import AWSFile
from collective.contentfiles2aws import awsfile
from collective.contentfiles2aws import config

MFactory = MessageFactory(config.PROJECTNAME)

createZClassForBase(awsfile.AWSFile, globals(), 'ZFile', 'AWSFile')

def initialize(context):

    context.registerClass(
        awsfile.AWSFile,
        permission=add_documents_images_and_files,
        constructors=(('fileAdd', awsfile.manage_addFileForm),
                       awsfile.manage_addFile),
        icon='images/File_icon.gif',
        legacy=(awsfile.manage_addFile,),
        )

    content_types, constructors, ftis = atapi.process_types(
        atapi.listTypes(config.PROJECTNAME),
        config.PROJECTNAME)

    for atype, constructor in zip(content_types, constructors):
        utils.ContentInit('%s: %s' % (config.PROJECTNAME, atype.portal_type),
            content_types      = (atype,),
            permission         = config.ADD_PERMISSIONS[atype.portal_type],
            extra_constructors = (constructor,),
            ).initialize(context)
