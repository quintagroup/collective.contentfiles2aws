from Products.CMFCore.utils import getToolByName

from collective.contentfiles2aws.config import PROJECTNAME


DEFAULT_PROFILE = 'profile-%s:default' % PROJECTNAME

def upgrade_step(upgrade_product, version): 
    """Decorator for updating the QuickInstaller of a upgrade"""
    def wrap_func(fn):
        def wrap_func_args(context,*args, **kw):
            p = getToolByName(context, 'portal_quickinstaller'
                ).get(upgrade_product)
            print "%s: Upgrading to %s" % (upgrade_product, version)
            setattr(p, 'installedversion', version)
            return fn(context,*args, **kw)
        return wrap_func_args
    return wrap_func


@upgrade_step(PROJECTNAME, '1.0')
def upgrade_to_1_0(context):
    context.runImportStepFromProfile(DEFAULT_PROFILE, 'catalog')
