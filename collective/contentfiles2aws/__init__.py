from zope.i18nmessageid import MessageFactory

from Products.CMFCore import utils
from Products.Archetypes import atapi

from collective.contentfiles2aws.content import AWSFile
from collective.contentfiles2aws.content import AWSImage
from collective.contentfiles2aws import config
from collective.contentfiles2aws import content_types_patch

MFactory = MessageFactory(config.PROJECTNAME)


def initialize(context):

    content_types, constructors, ftis = atapi.process_types(
        atapi.listTypes(config.PROJECTNAME),
        config.PROJECTNAME)

    for atype, constructor in zip(content_types, constructors):
        utils.ContentInit('%s: %s' % (config.PROJECTNAME, atype.portal_type),
            content_types      = (atype,),
            permission         = config.ADD_PERMISSIONS[atype.portal_type],
            extra_constructors = (constructor,),
            ).initialize(context)
